from odoo import http
from odoo.http import request

TOOLS_MODEL = "ai.business.tools.core"


class AIAssistantController(http.Controller):
    """Stable endpoints + minimal HTML chat."""

    def _core_ai_logic(self, message: str):
        import json, requests
        if message and message.strip().lower() in ("hi","hello","hey"):
            g = "Hi! Ask me about your Odoo data or tell me to create something (e.g., create a sales order …)."
            return {"text": g, "message": g, "tool_calls": [], "tool_results": []}

        ICP = request.env["ir.config_parameter"].sudo()
        provider = (ICP.get_param("ai_business_assistant.ai_provider") or "openai").strip()
        api_key = (ICP.get_param("ai_business_assistant.ai_api_key") or "").strip()
        model = (ICP.get_param("ai_business_assistant.ai_model") or "gpt-4o-mini").strip()
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

        ToolModel = request.env[TOOLS_MODEL].sudo()
        try:
            tool_schemas = ToolModel.tool_schemas()
        except Exception as e:
            return {"error": f"Tool model not available: {e}"}

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = base_url.rstrip("/") + "/chat/completions"
        sys_prompt = ("You are an Odoo business assistant. Use tools to answer questions "
                      "and to create/update records when asked. Keep answers short and plain.")

        payload = {
            "model": model,
            "messages": [{"role":"system","content":sys_prompt},{"role":"user","content":message}],
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
            return {"text":"(no content)","message":"(no content)","tool_calls":[],"tool_results":[]}
        msg = choices[0].get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        tool_results = []

        if tool_calls:
            import json as _json
            for tc in tool_calls[:5]:
                fn = (tc.get("function") or {}).get("name")
                args_str = (tc.get("function") or {}).get("arguments") or "{}"
                try:
                    args = _json.loads(args_str)
                except Exception:
                    args = {}
                try:
                    res = ToolModel.execute_tool(fn, args)
                    tool_results.append({"tool_call_id": tc.get("id"), "name": fn, "content": res})
                except Exception as e:
                    tool_results.append({"tool_call_id": tc.get("id"), "name": fn, "error": str(e)})
            tool_msgs = [{
                "role":"tool",
                "tool_call_id": tr["tool_call_id"],
                "name": tr["name"],
                "content": (_json.dumps(tr.get("content", tr.get("error","")), ensure_ascii=False))
            } for tr in tool_results]
            payload2 = {"model": model, "messages": payload["messages"] + [msg] + tool_msgs, "temperature": 0.2}
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

        text = msg.get("content") or "(empty)"
        return {"text": text, "message": text, "tool_calls": [], "tool_results": []}

    @http.route("/ai_assistant/query_http", type="http", auth="user", csrf=False, methods=["POST","GET"])
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
                return request.make_response('{"error":"Missing parameter: \'message\'"}',
                                             headers=[("Content-Type","application/json")], status=200)
            res = self._core_ai_logic(message)
            try:
                body = _json.dumps(res, ensure_ascii=False)
            except Exception:
                body = '{"text":"(serialization error)"}'
            return request.make_response(body, headers=[("Content-Type","application/json")], status=200)
        except Exception as e:
            return request.make_response('{"error":"%s"}' % str(e).replace('"','\"'),
                                         headers=[("Content-Type","application/json")], status=200)

    @http.route("/ai_assistant/query_rpc", type="json", auth="user", csrf=False, methods=["POST","GET"])
    def ai_query_json(self, message=None, **kw):
        try:
            if not message:
                message = (request.jsonrequest or {}).get("message")
            if not message:
                return {"error":"Missing parameter: 'message'"}
            return self._core_ai_logic(message)
        except Exception as e:
            return {"error": str(e)}

    @http.route("/ai_assistant_minimal", type="http", auth="user", csrf=False, methods=["GET"])
    def ai_minimal_page(self, **kw):
        html = """<!DOCTYPE html>
<html><head><meta charset=\"utf-8\"><title>AI Business Assistant</title>
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<style>
body { font-family: Arial, sans-serif; margin: 24px; }
.wrap { max-width: 820px; margin: 0 auto; }
h1 { margin: 0 0 12px; }
#log { border: 1px solid #ddd; padding: 12px; height: 320px; overflow:auto; border-radius:8px; }
#msg { width: 100%; padding:10px; border-radius:6px; border:1px solid #ccc; margin-top:10px; }
button { margin-top: 10px; padding: 10px 16px; border-radius: 6px; border: 0; background: #3b82f6; color: white; cursor: pointer;}
.item { margin: 6px 0; }
.you { color:#111; }
.ai { color:#0b5; }
.err { color:#c00; }
.meta { color:#666; font-size:12px; }
</style></head>
<body>
<div class=\"wrap\">
  <h1>AI Business Assistant</h1>
  <div id=\"log\"></div>
  <textarea id=\"msg\" rows=\"3\" placeholder=\"Ask: e.g., how many products do I have?\"></textarea>
  <button id=\"send\">Send</button>
  <p class=\"meta\">This page calls <code>/ai_assistant/query_http</code>.</p>
</div>
<script>
const log = document.getElementById('log');
const msg = document.getElementById('msg');
const btn = document.getElementById('send');
function addLine(cls, txt) {
  const div = document.createElement('div');
  div.className = 'item ' + cls;
  div.textContent = txt;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}
async function ask() {
  const q = msg.value.trim();
  if (!q) return;
  addLine('you', 'You: ' + q);
  msg.value='';
  try {
    const res = await fetch('/ai_assistant/query_http', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message: q})
    });
    const txt = await res.text();
    let jd = null;
    try { jd = JSON.parse(txt); } catch {}
    if (jd && (jd.text || jd.message)) addLine('ai', 'Assistant: ' + (jd.text || jd.message));
    else if (jd && jd.error) addLine('err', 'Assistant: ' + jd.error);
    else addLine('err', 'Assistant: Raw: ' + txt);
  } catch (e) { addLine('err', 'Network error: ' + e); }
}
btn.addEventListener('click', ask);
msg.addEventListener('keydown', (e)=>{ if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); ask(); }});
</script>
</body></html>"""
        return request.make_response(html, headers=[("Content-Type","text/html; charset=utf-8")], status=200)
