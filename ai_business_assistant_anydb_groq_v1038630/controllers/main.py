
from odoo import http
from odoo.http import request

TOOLS_MODEL = "ai.business.tools.core"


class AIAssistantController(http.Controller):
    """HTTP + JSON endpoints for the AI Business Assistant."""

    # -----------------------------
    # Core logic (never raises 500)
    # -----------------------------
    def _core_ai_logic(self, message: str):
        import json, requests

        # Greetings shortcut
        if message and message.strip().lower() in ("hi", "hello", "hey"):
            greeting = "Hi! Ask me about your Odoo data or tell me to create something (e.g., \"create a sales order …\")."
            return {"text": greeting, "message": greeting, "tool_calls": [], "tool_results": []}

        # Load settings
        ICP = request.env["ir.config_parameter"].sudo()
        provider = (ICP.get_param("ai_business_assistant.ai_provider") or "openai").strip()
        api_key = (ICP.get_param("ai_business_assistant.ai_api_key") or "").strip()
        model = (ICP.get_param("ai_business_assistant.ai_model") or "gpt-4o-mini").strip()

        # Base URL selection (OpenAI-compatible)
        base_url = (ICP.get_param("ai_business_assistant.ai_base_url") or "").strip()
        if not base_url:
            if provider == "groq":
                base_url = "https://api.groq.com/openai/v1"
            elif provider == "ollama":
                base_url = "http://localhost:11434/v1"
            else:
                base_url = "https://api.openai.com/v1"

        if not api_key:
            return {"error": "Missing API key"}

        # Tool schemas
        ToolModel = request.env[TOOLS_MODEL].sudo()
        tool_schemas = ToolModel.tool_schemas()

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = base_url.rstrip("/") + "/chat/completions"

        sys_prompt = (
            "You are an Odoo business assistant. "
            "Use the provided tools to answer questions about the database and to create/update records on command. "
            "Keep answers short and plain. If data is missing, ask for minimal clarification."
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": message},
            ],
            "tools": tool_schemas,
            "tool_choice": "auto",
            "temperature": 0.2,
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            jd = r.json()
        except Exception as e:
            return {"error": f"Upstream call failed: {e}"}

        if r.status_code >= 400:
            return {"error": f"Upstream error {r.status_code}: {jd}"}

        choices = jd.get("choices") or []
        if not choices:
            return {"text": "(no content)", "message": "(no content)", "tool_calls": [], "tool_results": []}

        msg = choices[0].get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        tool_results = []

        # Execute tools if requested
        if tool_calls:
            import json as _json
            for tc in tool_calls[:5]:
                name = (tc.get("function") or {}).get("name")
                args_str = (tc.get("function") or {}).get("arguments") or "{}"
                try:
                    args = _json.loads(args_str)
                except Exception:
                    args = {}
                try:
                    res = ToolModel.execute_tool(name, args)
                    tool_results.append({"tool_call_id": tc.get("id"), "name": name, "content": res})
                except Exception as e:
                    tool_results.append({"tool_call_id": tc.get("id"), "name": name, "error": str(e)})

            # Send results back for a final summary
            tool_msgs = [
                {
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "name": tr["name"],
                    "content": _json.dumps(tr.get("content", tr.get("error", "")), ensure_ascii=False),
                }
                for tr in tool_results
            ]
            payload2 = {
                "model": model,
                "messages": payload["messages"] + [msg] + tool_msgs,
                "temperature": 0.2,
            }

            try:
                r2 = requests.post(url, headers=headers, json=payload2, timeout=60)
                jd2 = r2.json()
            except Exception as e:
                txt = f"(tool-call roundtrip failed: {e})"
                return {"text": txt, "message": txt, "tool_calls": tool_calls, "tool_results": tool_results}

            if r2.status_code >= 400:
                txt = f"Upstream error {r2.status_code}: {jd2}"
                return {"text": txt, "message": txt, "tool_calls": tool_calls, "tool_results": tool_results}

            choices2 = jd2.get("choices") or []
            final_msg = choices2[0].get("message", {}) if choices2 else {}
            text = final_msg.get("content") or "(empty)"
            return {"text": text, "message": text, "tool_calls": tool_calls, "tool_results": tool_results}

        # No tools used
        text = msg.get("content") or "(empty)"
        return {"text": text, "message": text, "tool_calls": [], "tool_results": []}

    # -----------------------------
    # HTTP (GET/POST) route — always 200 with JSON body
    # -----------------------------
    @http.route("/ai_assistant/query_http", type="http", auth="user", csrf=False, methods=["POST", "GET"])
    def ai_query_http(self, **kw):
        import json as _json
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True)
            message = None
            if raw:
                try:
                    body = _json.loads(raw)
                    message = body.get("message")
                except Exception:
                    pass
            if not message:
                message = request.httprequest.args.get("message")

            if not message:
                return request.make_response(
                    '{"error":"Missing parameter: \'message\'"}',
                    headers=[("Content-Type", "application/json")],
                    status=200,
                )

            res = self._core_ai_logic(message)
            try:
                body = _json.dumps(res, ensure_ascii=False)
            except Exception:
                body = '{"text":"(serialization error)"}'
            return request.make_response(body, headers=[("Content-Type", "application/json")], status=200)
        except Exception as e:
            return request.make_response(
                '{"error":"%s"}' % str(e).replace('"', '\"'),
                headers=[("Content-Type", "application/json")],
                status=200,
            )

    # -----------------------------
    # JSON-RPC route (returns dict)
    # -----------------------------
    @http.route("/ai_assistant/query_rpc", type="json", auth="user", csrf=False, methods=["POST", "GET"])
    def ai_query_json(self, message=None, **kw):
        try:
            if not message:
                message = (request.jsonrequest or {}).get("message")
            if not message:
                return {"error": "Missing parameter: 'message'"}
            return self._core_ai_logic(message)
        except Exception as e:
            return {"error": str(e)}
