
import json
import logging
import requests

from odoo import http
from odoo.http import request

SYSTEM_PROMPT = (
    "You are an Odoo Business Assistant. "
    "If a question requires data, use the provided tools. "
    "Prefer generic tools (count_records, search_read, read_group) when unsure. "
)

TOOLS_MODEL = "ai.business.tools.core"


class AIAssistantController(http.Controller):
    _logger = logging.getLogger(__name__)

    # ----------- Utility -----------
    def _provider_config(self):
        ICP = request.env["ir.config_parameter"].sudo()
        enabled = ICP.get_param("ai_business_assistant.ai_enabled", "True") == "True"
        api_key = ICP.get_param("ai_business_assistant.ai_api_key") or None
        return {
            "enabled": enabled,
            "provider": ICP.get_param("ai_business_assistant.ai_provider", "openai"),
            "api_key": api_key,
            "model": ICP.get_param("ai_business_assistant.ai_model", "llama-3.1-8b-instant"),
            "base_url": (ICP.get_param("ai_business_assistant.ai_base_url") or "https://api.groq.com/openai/v1").rstrip("/"),
        }

    def _tool_schemas(self):
        return request.env[TOOLS_MODEL].sudo().tool_schemas()

    def _chat_completion(self, messages, tools=None):
        cfg = self._provider_config()
        if not cfg.get("enabled"):
            return {"error": "AI Assistant disabled"}
        if not cfg.get("api_key"):
            return {"error": "Missing API key"}

        headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
        url = f"{cfg['base_url']}/chat/completions"
        payload = {"model": cfg["model"], "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code >= 400:
                return {"error": f"Upstream error {resp.status_code}: {resp.text}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def _execute_tools_from_response(self, response_json):
        tool_calls_payloads = []
        tool_results_payloads = []
        try:
            choice = (response_json.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            tool_calls = message.get("tool_calls") or []
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name")
                args_raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw)
                except Exception:
                    args = {}
                result = request.env[TOOLS_MODEL].sudo().execute_tool(name, args)
                tool_calls_payloads.append({"id": tc.get("id"), "name": name, "arguments": args})
                tool_results_payloads.append({"tool_call_id": tc.get("id"), "name": name, "content": result})
        except Exception as e:
            tool_results_payloads.append({"error": str(e)})
        return tool_calls_payloads, tool_results_payloads

    def _naive_intent(self, message):
        m = (message or "").lower()
        if any(k in m for k in ["how many products", "product count", "number of products", "count products"]):
            return ("count_products", {"include_services": False})
        if "profit" in m:
            from datetime import date
            start = date(date.today().year, 1, 1).isoformat()
            end = date.today().isoformat()
            return ("get_profit", {"start_date": start, "end_date": end})
        if any(k in m for k in ["how many", "count"]) and "product" not in m:
            return ("count_records", {"model": "res.partner"})
        return (None, None)

    # ----------- Routes -----------
    @http.route("/ai_assistant_ping", type="http", auth="user")
    def ai_ping(self, **kw):
        return request.make_response("OK", headers=[("Content-Type", "text/plain; charset=utf-8")])

    @http.route("/ai_assistant/query", type="json", auth="user", csrf=False)
    def ai_query(self, message=None, **kw):
        kwargs = kw or {}
        from odoo.http import request
        params = request.jsonrequest or {}
        if message is None:
            message = params.get("message") or request.httprequest.args.get("message")
        if not message:
            return {"error": "Missing parameter: \'message\'"}
        try:
            message = (kwargs or {}).get("message")
            if message is None:
                message = ((kwargs or {}).get("params") or {}).get("message")
            message = message or ""
            if not isinstance(message, str) or not message.strip():
                return {"error": "Missing parameter: 'message'"}

            msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ]
            tools = self._tool_schemas()

            first = self._chat_completion(messages=msgs, tools=tools)
            if isinstance(first, dict) and first.get("error"):
                if "tool_use_failed" in first.get("error", ""):
                    name, args = self._naive_intent(message)
                    if name:
                        result = request.env[TOOLS_MODEL].sudo().execute_tool(name, args)
                        final_text = f"Result for {name}: " + json.dumps(result)
                        return {"text": final_text, "tool_calls": [{"name": name, "arguments": args}], "tool_results": [{"content": result}]}
                return {"error": first["error"]}

            tool_calls, tool_results = self._execute_tools_from_response(first)

            if tool_calls:
                msgs.append(first["choices"][0]["message"])
                for tr in tool_results:
                    msgs.append({"role": "tool", "tool_call_id": tr.get("tool_call_id"), "content": json.dumps(tr.get("content"))})
                second = self._chat_completion(messages=msgs, tools=tools)
                if isinstance(second, dict) and second.get("error"):
                    return {"error": second["error"]}
                final_text = (second.get("choices") or [{}])[0].get("message", {}).get("content", "")
            else:
                final_text = (first.get("choices") or [{}])[0].get("message", {}).get("content", "")

            if not final_text:
                name, args = self._naive_intent(message)
                if name:
                    result = request.env[TOOLS_MODEL].sudo().execute_tool(name, args)
                    final_text = f"Result for {name}: " + json.dumps(result)
                    tool_calls = tool_calls or [{"name": name, "arguments": args}]
                    tool_results = tool_results or [{"content": result}]
                else:
                    final_text = "I couldn't find a direct answer. Try: profit, revenue, expenses, product counts, top products, search_read, read_group."

            return {"text": final_text, "tool_calls": tool_calls, "tool_results": tool_results}
        except Exception as e:
            return {"error": str(e)}

    
@http.route("/ai_assistant/query_http", type="json", auth="user", csrf=False, methods=["POST","GET"])
def ai_query(self, message=None, **kw):
    from odoo.http import request
    import json, requests
    try:
        params = request.jsonrequest or {}
        if message is None:
            message = params.get("message") or request.httprequest.args.get("message")
        if not message:
            return {"error": "Missing parameter: 'message'"}

        # Friendly greeting
        if message.strip().lower() in ("hi", "hello", "hey"):
            return {"text": "Hi! Ask me about your Odoo data or tell me to create something (e.g., 'create a sales order ...').", "tool_calls": [], "tool_results": []}

        ICP = request.env['ir.config_parameter'].sudo()
        provider = (ICP.get_param("ai_business_assistant.ai_provider") or "openai").strip()
        api_key = (ICP.get_param("ai_business_assistant.ai_api_key") or "").strip()
        model = (ICP.get_param("ai_business_assistant.ai_model") or "gpt-4o-mini").strip()
        base_url = (ICP.get_param("ai_business_assistant.ai_base_url") or "https://api.openai.com/v1").strip()

        if not api_key:
            return {"error": "Missing API key"}

        ToolModel = request.env["ai.business.tools.core"].sudo()
        tool_schemas = ToolModel.tool_schemas()

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = base_url.rstrip("/") + "/chat/completions"

        sys_prompt = "You are an Odoo assistant. Use provided tools to answer questions about the database and to create or update records on command. Keep answers short and plain. If data is missing, ask for the minimal clarification."

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

        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        jd = r.json()
        if r.status_code >= 400:
            return {"error": f"Upstream error {r.status_code}: {json.dumps(jd, ensure_ascii=False)}"}

        choices = jd.get("choices") or []
        if not choices:
            return {"text": "(no content)", "tool_calls": [], "tool_results": []}

        msg = choices[0].get("message", {}) or {}
        tool_calls = msg.get("tool_calls") or []
        tool_results = []

        # Execute tool calls if any
        if tool_calls:
            for tc in tool_calls[:5]:
                name = (tc.get("function") or {}).get("name")
                args_str = (tc.get("function") or {}).get("arguments") or "{}"
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}
                try:
                    res = ToolModel.execute_tool(name, args)
                    tool_results.append({"tool_call_id": tc.get("id"), "name": name, "content": res})
                except Exception as e:
                    tool_results.append({"tool_call_id": tc.get("id"), "name": name, "error": str(e)})

            # Send results back for final assistant text
            tool_msgs = [
                {"role": "tool", "tool_call_id": tr["tool_call_id"], "name": tr["name"], "content": json.dumps(tr.get("content", tr.get("error", "")), ensure_ascii=False)}
                for tr in tool_results
            ]
            payload2 = {
                "model": model,
                "messages": payload["messages"] + [msg] + tool_msgs,
                "temperature": 0.2,
            }
            r2 = requests.post(url, headers=headers, data=json.dumps(payload2), timeout=60)
            jd2 = r2.json()
            if r2.status_code >= 400:
                txt = f"Upstream error {r2.status_code}: {json.dumps(jd2, ensure_ascii=False)}"
                return {"text": txt, "tool_calls": tool_calls, "tool_results": tool_results}
            choices2 = jd2.get("choices") or []
            final_msg = choices2[0].get("message", {}) if choices2 else {}
            text = final_msg.get("content") or "(empty)"
            # Return both 'text' and 'message' keys for frontend compatibility
            return {"text": text, "message": text, "tool_calls": tool_calls, "tool_results": tool_results}

        # No tools used; return assistant content
        text = msg.get("content") or "(empty)"
        return {"text": text, "message": text, "tool_calls": [], "tool_results": []}

    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

    @http.route("/ai_assistant_diag", type="http", auth="user")
    def ai_diag(self, **kw):
        cfg = self._provider_config()
        redacted_cfg = {
            "enabled": cfg.get("enabled"),
            "provider": cfg.get("provider"),
            "model": cfg.get("model"),
            "base_url": cfg.get("base_url"),
            "api_key_present": bool(cfg.get("api_key")),
        }
        test = {"ok": False, "status_code": None, "text": None, "error": None}
        try:
            if cfg.get("api_key"):
                payload = {"model": cfg["model"], "messages": [{"role": "user", "content": "Say OK"}]}
                headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
                url = f"{cfg['base_url']}/chat/completions"
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                test["status_code"] = resp.status_code
                if resp.status_code < 400:
                    data = resp.json()
                    msg = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
                    test["ok"] = True
                    test["text"] = (msg or "")[:200]
                else:
                    test["error"] = (resp.text or "")[:500]
            else:
                test["error"] = "Missing API key"
        except Exception as e:
            test["error"] = str(e)

        html = "<h2>AI Assistant Diagnostics</h2>"
        html += "<pre>Config (redacted):\\n" + json.dumps(redacted_cfg, indent=2) + "</pre>"
        html += "<pre>Ping:\\n" + json.dumps(test, indent=2) + "</pre>"
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route("/ai_assistant_plain_js", type="http", auth="user")
    def ai_plain_js(self, **kw):
        js = """
document.addEventListener('DOMContentLoaded', function(){
  function el(id){ return document.getElementById(id); }
  function appendLog(text, who){
    var log = el('chat-log');
    if(!log) return;
    var line = document.createElement('div');
    var strong = document.createElement('strong');
    strong.textContent = (who||'') + (who?': ':''); 
    line.appendChild(strong);
    line.appendChild(document.createTextNode(String(text || '')));
    line.style.margin = '6px 0';
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  }
  function speak(text){
    try { var u = new SpeechSynthesisUtterance(text); window.speechSynthesis.speak(u); } catch(e){}
  }
  async function sendMsg(message){
    appendLog(message, 'You');
    try{
      var res = await fetch('/ai_assistant/query_http', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({message: message})
      });
      var txt = await res.text();
      var payload = null;
      try { payload = JSON.parse(txt); } catch(e){ payload = {error: 'Invalid JSON', text: (txt||'').substring(0,200)}; }
      if(!res.ok){
        appendLog((payload && (payload.error||payload.message)) || ('HTTP '+res.status), 'Assistant');
        return;
      }
      if(payload && payload.text){
        appendLog(payload.text, 'Assistant'); speak(payload.text);
      } else if(payload && payload.error){
        appendLog('Error: '+(typeof payload.error==='string'?payload.error:JSON.stringify(payload.error)), 'Assistant');
      } else {
        appendLog('I received a response but it did not include a message.', 'Assistant');
      }
    }catch(err){
      appendLog('Error: '+(err && err.message ? err.message : 'Unknown'), 'Assistant');
    }
  }
  var input = el('chat-input');
  var sendBtn = el('send-btn');
  var voiceBtn = el('voice-btn');
  if(sendBtn) sendBtn.addEventListener('click', function(){ var v=(input&&input.value||'').trim(); if(v){ sendMsg(v); input.value=''; }});
  if(input) input.addEventListener('keydown', function(e){ if(e.key==='Enter'){ var v=(input.value||'').trim(); if(v){ sendMsg(v); input.value=''; }} });
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR && voiceBtn){ voiceBtn.disabled=true; voiceBtn.title='Web Speech API not supported'; }
  if(SR && voiceBtn){
    var recognition = new SR(); recognition.lang='en-US'; recognition.interimResults=false; recognition.maxAlternatives=1;
    var listening=false;
    voiceBtn.addEventListener('mousedown', function(){ listening=true; voiceBtn.classList.add('danger'); recognition.start(); });
    voiceBtn.addEventListener('mouseup', function(){ if(!listening) return; listening=false; voiceBtn.classList.remove('danger'); try{ recognition.stop(); }catch(e){} });
    voiceBtn.addEventListener('mouseleave', function(){ if(!listening) return; listening=false; voiceBtn.classList.remove('danger'); try{ recognition.stop(); }catch(e){} });
    recognition.addEventListener('result', function(e){ var t=e.results[0][0].transcript; if(input){ input.value=t; } sendMsg(t); });
    recognition.addEventListener('error', function(e){ appendLog('Voice error: '+e.error, 'System'); });
  }
});
""".strip()
        return request.make_response(js, headers=[("Content-Type", "application/javascript; charset=utf-8")])

    @http.route("/ai_assistant_plain", type="http", auth="user")
    def voice_page_plain(self, **kw):
        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>AI Business Assistant</title>
<style>
body{font-family:Arial,Helvetica,sans-serif;margin:24px}
.card{border:1px solid #ddd;border-radius:10px;padding:16px;max-width:900px}
#chat-log{height:260px;overflow:auto;border:1px solid #e5e5e5;padding:8px;border-radius:6px;margin-bottom:12px;white-space:pre-wrap}
.row{display:flex;gap:8px}
input[type=text]{flex:1;padding:8px;border-radius:6px;border:1px solid #ccc}
button{padding:8px 12px;border-radius:8px;border:1px solid #999;cursor:pointer}
button.danger{background:#c33;color:#fff;border-color:#a22}
small{color:#666}
</style></head>
<body>
<h1>AI Business Assistant</h1>
<div class="card">
  <div id="chat-log"></div>
  <div class="row">
    <input id="chat-input" type="text" placeholder="Type your question"/>
    <button id="send-btn">Send</button>
    <button id="voice-btn">Hold to talk</button>
  </div>
  <small>Voice uses your browser Web Speech API.</small>
</div>
<script src="/ai_assistant_plain_js" defer></script>
</body></html>"""
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])


    @http.route("/ai_assistant/query_json", type="http", auth="user", csrf=False, methods=["GET"])
    def ai_query_json_proxy(self, **kw):
        from odoo.http import request
        message = request.httprequest.args.get("message")
        if not message:
            return request.make_response('{"error":"Missing parameter: \'message\'"}', headers=[("Content-Type","application/json")])
        # call the json route
        res = self.ai_query(message=message)
        # If Odoo returns a dict (json), serialize
        try:
            import json
            body = json.dumps(res)
        except Exception:
            body = str(res)
        return request.make_response(body, headers=[("Content-Type","application/json")])
    