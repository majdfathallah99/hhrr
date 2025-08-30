
import json
import logging
import requests

from odoo import http, fields
from odoo.http import request

SYSTEM_PROMPT = (
    "You are an Odoo Business Assistant. "
    "If a question requires data or actions, use the provided tools. "
    "For create/update requests, confirm the details in your own words and then call the tool once. "
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

    def _execute_tools(self, response_json):
        tool_calls = []
        tool_results = []
        try:
            choice = (response_json.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            for tc in message.get("tool_calls") or []:
                fn = (tc.get("function") or {})
                name = fn.get("name")
                args_raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw)
                except Exception:
                    args = {}
                result = request.env[TOOLS_MODEL].sudo().execute_tool(name, args)
                tool_calls.append({"id": tc.get("id"), "name": name, "arguments": args})
                tool_results.append({"tool_call_id": tc.get("id"), "name": name, "content": result})
        except Exception as e:
            tool_results.append({"error": str(e)})
        return tool_calls, tool_results

    @http.route("/ai_assistant_plain", type="http", auth="user")
    def page(self, **kw):
        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>AI Business Assistant</title>
<style>
body{font-family:Arial,Helvetica,sans-serif;margin:24px}
.card{border:1px solid #ddd;border-radius:10px;padding:16px;max-width:900px}
#chat-log{height:300px;overflow:auto;border:1px solid #e5e5e5;padding:8px;border-radius:6px;margin-bottom:12px;white-space:pre-wrap}
.row{display:flex;gap:8px}
input[type=text]{flex:1;padding:8px;border-radius:6px;border:1px solid #ccc}
button{padding:8px 12px;border-radius:8px;border:1px solid #999;cursor:pointer}
small{color:#666}
</style></head>
<body>
<h1>AI Business Assistant</h1>
<div class="card">
  <div id="chat-log"></div>
  <div class="row">
    <input id="chat-input" type="text" placeholder="Type your question"/>
    <button id="send-btn">Send</button>
  </div>
  <small>Example: "create a sales order for Deco Addict, 2 x Large Desk", or "profit this year".</small>
</div>
<script>
document.addEventListener('DOMContentLoaded', function(){
  function el(i){return document.getElementById(i)}
  function log(t,who){var l=el('chat-log'); var d=document.createElement('div'); d.style.margin='6px 0'; d.innerHTML='<strong>'+who+':</strong> '+(t||''); l.appendChild(d); l.scrollTop=l.scrollHeight;}
  async function sendMsg(msg){
    log(msg,'You');
    try{
      const res = await fetch('/ai_assistant/query_http',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({message:msg})});
      const txt = await res.text();
      let data=null; try{data=JSON.parse(txt);}catch(e){data={error:'Invalid JSON',text:txt.substring(0,200)}}
      if(!res.ok){ log((data.error||('HTTP '+res.status)),'Assistant'); return; }
      log(data.text || data.error || 'No reply','Assistant');
    }catch(e){ log('Error: '+e.message,'Assistant'); }
  }
  const input = el('chat-input'); document.getElementById('send-btn').addEventListener('click',()=>{const v=(input.value||'').trim(); if(v){sendMsg(v); input.value='';}});
  input.addEventListener('keydown',e=>{ if(e.key==='Enter'){const v=(input.value||'').trim(); if(v){sendMsg(v); input.value='';}});
});
</script>
</body></html>"""
        return request.make_response(html, headers=[("Content-Type","text/html; charset=utf-8")])

    @http.route("/ai_assistant/query_http", type="http", auth="user", csrf=False, methods=["POST","GET"])
    def query_http(self, **kw):
        try:
            if request.httprequest.method == "GET":
                message = request.httprequest.args.get("message") or ""
            else:
                raw = (request.httprequest.data or b"").decode("utf-8") or "{}"
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = {}
                message = (payload.get("message") or (payload.get("params") or {}).get("message") or "")
            messages = [
                {"role":"system","content": SYSTEM_PROMPT},
                {"role":"user","content": message},
            ]
            tools = self._tool_schemas()
            first = self._chat(messages, tools=tools)
            if isinstance(first, dict) and first.get("error"):
                return request.make_response(json.dumps({"error": first["error"]}), headers=[("Content-Type","application/json")], status=200)
            tool_calls, tool_results = self._execute_tools(first)
            if tool_calls:
                messages.append(first["choices"][0]["message"])
                for tr in tool_results:
                    messages.append({"role": "tool", "tool_call_id": tr.get("tool_call_id"), "content": json.dumps(tr.get("content"))})
                second = self._chat(messages, tools=tools)
                if isinstance(second, dict) and second.get("error"):
                    payload = {"error": second["error"]}
                else:
                    payload = {"text": (second.get("choices") or [{}])[0].get("message", {}).get("content", ""), "tool_calls": tool_calls, "tool_results": tool_results}
            else:
                payload = {"text": (first.get("choices") or [{}])[0].get("message", {}).get("content", ""), "tool_calls": [], "tool_results": []}
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
