
import json
import requests
from odoo import http
from odoo.http import request

SYSTEM_PROMPT = (
    "You are an Odoo Business Assistant. "
    "Your job is to answer questions about the user's Odoo data. "
    "If a question requires data, call a tool. "
    "Prefer precise numbers with currency where relevant. "
    "Always state the date ranges and company name you used. "
    "If the user asks for years like 'this year', interpret using the server timezone."
)

class AIAssistantController(http.Controller):
    def _provider_config(self):
        ICP = request.env["ir.config_parameter"].sudo()
        return {
            "enabled": ICP.get_param("ai_business_assistant.ai_enabled", "True") == "True",
            "provider": ICP.get_param("ai_business_assistant.ai_provider", "openai"),
            "api_key": ICP.get_param("ai_business_assistant.ai_api_key"),
            "model": ICP.get_param("ai_business_assistant.ai_model", "gpt-4o-mini"),
            "base_url": ICP.get_param("ai_business_assistant.ai_base_url") or "https://api.openai.com/v1",
        }

    def _tool_schemas(self):
        return request.env["ai.business.tools"].sudo().tool_schemas()

    def _chat_completion(self, messages, tools=None):
        cfg = self._provider_config()
        if not cfg.get("enabled"):
            return {"error": "AI Assistant disabled"}
        if cfg["provider"] in ("openai", "azure_openai", "ollama"):
            headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
            url = cfg["base_url"].rstrip("/") + "/chat/completions"
            payload = {"model": cfg["model"], "messages": messages}
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code >= 400:
                return {"error": f"Upstream error {resp.status_code}: {resp.text}"}
            return resp.json()
        return {"error": "Unsupported provider"}

    def _execute_tools_from_response(self, response_json):
        tool_calls_payloads = []
        tool_results_payloads = []
        try:
            choice = response_json.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", []) or []
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name")
                args_raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw)
                except Exception:
                    args = {}
                result = request.env["ai.business.tools"].sudo().execute_tool(name, args)
                tool_calls_payloads.append({"id": tc.get("id"), "name": name, "arguments": args})
                tool_results_payloads.append({"tool_call_id": tc.get("id"), "name": name, "content": result})
            return tool_calls_payloads, tool_results_payloads
        except Exception as e:
            return [], [{"error": str(e)}]

    @http.route("/ai_assistant/query", type="json", auth="user")
    def ai_query(self, message):
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        tools = self._tool_schemas()
        first = self._chat_completion(messages=msgs, tools=tools)
        if first.get("error"):
            return first

        tool_calls, tool_results = self._execute_tools_from_response(first)

        if tool_calls:
            msgs.append(first["choices"][0]["message"])
            for tr in tool_results:
                msgs.append({"role": "tool", "tool_call_id": tr.get("tool_call_id"), "content": json.dumps(tr.get("content"))})
            second = self._chat_completion(messages=msgs, tools=tools)
            final_text = second.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            final_text = first.get("choices", [{}])[0].get("message", {}).get("content", "")

        request.env["ai.assistant.log"].sudo().create({
            "name": message,
            "response_text": final_text,
            "tool_calls_json": json.dumps(tool_calls, ensure_ascii=False),
            "tool_results_json": json.dumps(tool_results, ensure_ascii=False),
        })

        return {"text": final_text, "tool_calls": tool_calls, "tool_results": tool_results}

    @http.route("/ai_assistant", type="http", auth="user", website=True)
    def voice_page(self, **kw):
        values = {}
        return request.render("ai_business_assistant.template_ai_voice_page", values)
