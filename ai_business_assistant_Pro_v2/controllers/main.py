
import json
import logging
import requests

from odoo import http
from odoo.http import request

SYSTEM_PROMPT = (
    "You are an Odoo Business Assistant. "
    "Use the provided tools to read/write data. "
    "When the user asks to create/update/delete, restate the intent briefly then call ONE tool."
)

TOOLS_MODEL = "ai.business.tools.core"

class AIAssistantController(http.Controller):
    _logger = logging.getLogger(__name__)

    def _provider_config(self):
        ICP = request.env['ir.config_parameter'].sudo()
        return {
            "enabled": ICP.get_param("ai_business_assistant.ai_enabled", "True") == "True",
            "provider": ICP.get_param("ai_business_assistant.ai_provider", "openai"),
            "api_key": ICP.get_param("ai_business_assistant.ai_api_key") or None,
            "model": ICP.get_param("ai_business_assistant.ai_model", "llama-3.1-8b-instant"),
            "base_url": (ICP.get_param("ai_business_assistant.ai_base_url") or "https://api.groq.com/openai/v1").rstrip("/"),
        }

    def _tool_schemas(self):
        return request.env[TOOLS_MODEL].sudo().tool_schemas()

    def _chat(self, messages, tools=None):
        cfg = self._provider_config()
        if not cfg["enabled"]:
            return {"error": "AI disabled"}
        if not cfg["api_key"]:
            return {"error": "Missing API key"}
        headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
        url = f"{cfg['base_url']}/chat/completions"
        payload = {"model": cfg["model"], "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code >= 400:
                return {"error": f"Upstream error {r.status_code}: {r.text}"}
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _execute_tools(self, resp):
        tool_calls, tool_results = [], []
        try:
            choice = (resp.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            for tc in msg.get("tool_calls") or []:
                fn = (tc.get("function") or {})
                name = fn.get("name")
                args_raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw)
                except Exception:
                    args = {}
                try:
                    out = request.env[TOOLS_MODEL].sudo().execute_tool(name, args)
                    tool_calls.append({"id": tc.get("id"), "name": name, "arguments": args})
                    tool_results.append({"tool_call_id": tc.get("id"), "name": name, "content": out})
                except Exception as e:
                    tool_results.append({"tool_call_id": tc.get("id"), "name": name, "error": str(e)})
        except Exception as e:
            tool_results.append({"error": str(e)})
        return tool_calls, tool_results

    @http.route("/ai_assistant_plain", type="http", auth="user")
    def page(self, **kw):
        return request.make_response("""
<!doctype html><html><head><meta charset='utf-8'><title>AI Business Assistant</title>
<style>body{font-family:system-ui,Arial;margin:24px}.card{max-width:900px;border:1px solid #ddd;border-radius:10px;padding:16px}
#chat{height:320px;border:1px solid #eee;border-radius:8px;padding:8px;overflow:auto;white-space:pre-wrap}
.row{display:flex;gap:8px;margin-top:8px}input{flex:1;padding:10px;border:1px solid #ccc;border-radius:8px}button{padding:10px 14px;border:1px solid #999;border-radius:8px;cursor:pointer}
small{color:#666}</style></head><body>
<h1>AI Business Assistant</h1>
<div class='card'>
  <div id='chat'></div>
  <div class='row'>
    <input id='q' placeholder='Ask anything about your Odoo...'><button id='go'>Send</button>
  </div>
  <small>Try: "create a sales order for Deco Addict 2 × Large Desk and confirm", or "top customers this year".</small>
</div>
<script>
const chat = document.getElementById('chat'); const q = document.getElementById('q'); const go = document.getElementById('go');
function log(who, text){const d=document.createElement('div'); d.innerHTML='<b>'+who+':</b> '+(text||''); chat.appendChild(d); chat.scrollTop=chat.scrollHeight;}
async function send(msg){log('You', msg); try{ const r=await fetch('/ai_assistant/query_http',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({message:msg})}); const t=await r.text(); let data=null; try{data=JSON.parse(t);}catch(e){data={error:'Invalid JSON',raw:t}}; log('Assistant', data.text || data.error || '(no reply)'); }catch(e){ log('Assistant','Error: '+e.message);} }
go.onclick=()=>{const v=(q.value||'').trim(); if(v){ send(v); q.value=''; }}; q.addEventListener('keydown',e=>{ if(e.key==='Enter'){go.click();} });
</script></body></html>
        """, headers=[("Content-Type","text/html; charset=utf-8")])

    @http.route("/ai_assistant/query_http", type="http", auth="user", csrf=False, methods=["POST","GET"])
    def query_http(self, **kw):
        try:
            if request.httprequest.method == "GET":
                message = request.httprequest.args.get("message") or ""
            else:
                raw = (request.httprequest.data or b"").decode("utf-8") or "{}"
                try: payload = json.loads(raw)
                except Exception: payload = {}
                message = (payload.get("message") or (payload.get("params") or {}).get("message") or "")
            messages = [
                {"role":"system","content": SYSTEM_PROMPT},
                {"role":"user","content": message},
            ]
            tools = self._tool_schemas()
            first = self._chat(messages, tools=tools)
            if isinstance(first, dict) and first.get("error"):
                return request.make_response(json.dumps({"error": first["error"]}), headers=[("Content-Type","application/json")], status=200)
            calls, results = self._execute_tools(first)
            if calls:
                messages.append(first["choices"][0]["message"])
                for tr in results:
                    messages.append({"role":"tool","tool_call_id": tr.get("tool_call_id"), "content": json.dumps(tr.get("content"))})
                second = self._chat(messages, tools=tools)
                if isinstance(second, dict) and second.get("error"):
                    payload = {"error": second["error"]}
                else:
                    payload = {"text": (second.get("choices") or [{}])[0].get("message",{}).get("content",""), "tool_calls": calls, "tool_results": results}
            else:
                payload = {"text": (first.get("choices") or [{}])[0].get("message",{}).get("content",""), "tool_calls": [], "tool_results": []}
            return request.make_response(json.dumps(payload), headers=[("Content-Type","application/json")], status=200)
        except Exception as e:
            return request.make_response(json.dumps({"error": str(e)}), headers=[("Content-Type","application/json")], status=200)

    @http.route("/ai_assistant_diag", type="http", auth="user")
    def diag(self, **kw):
        ICP = request.env['ir.config_parameter'].sudo()
        cfg = {
            "enabled": ICP.get_param("ai_business_assistant.ai_enabled"),
            "provider": ICP.get_param("ai_business_assistant.ai_provider"),
            "model": ICP.get_param("ai_business_assistant.ai_model"),
            "base_url": ICP.get_param("ai_business_assistant.ai_base_url"),
            "api_key_present": bool(ICP.get_param("ai_business_assistant.ai_api_key")),
            "superuser": ICP.get_param("ai_business_assistant.superuser"),
        }
        return request.make_response("<pre>"+json.dumps(cfg, indent=2)+"</pre>", headers=[("Content-Type","text/html; charset=utf-8")])
