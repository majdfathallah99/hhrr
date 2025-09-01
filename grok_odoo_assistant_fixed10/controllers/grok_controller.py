# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from markupsafe import escape

def _get_param(key, default=''):
    return request.env['ir.config_parameter'].sudo().get_param(key, default)

def _set_param(key, val):
    request.env['ir.config_parameter'].sudo().set_param(key, val or '')

CONFIG_HTML = '''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Assistant Settings</title></head>
<body>
<h1>Assistant Settings</h1>
<form method="post" action="/grok/config/save">
  <div>
    <label>Provider</label><br/>
    <select name="provider">
      <option value="xai" %SEL_XAI%>x.ai (Grok)</option>
      <option value="groq" %SEL_GROQ%>Groq (OpenAI-compatible)</option>
      <option value="custom" %SEL_CUSTOM%>Custom Endpoint</option>
    </select>
  </div>
  <div>
    <label>Endpoint URL (for Custom)</label><br/>
    <input type="text" name="endpoint_url" value="%ENDPOINT%" style="width:600px;" placeholder="https://.../chat/completions"/>
  </div>
  <div>
    <label>API Key</label><br/>
    <input type="password" name="api_key" value="%API_KEY%" style="width:420px;"/>
  </div>
  <div>
    <label>Model</label><br/>
    <input type="text" name="model" value="%MODEL%" placeholder="grok-4-latest or llama-3.1-8b-instant"/>
  </div>
  <div>
    <label>Temperature</label><br/>
    <input type="number" name="temperature" step="0.1" value="%TEMP%" />
  </div>
  <div>
    <label>Allowed Odoo Models (comma separated)</label><br/>
    <input type="text" name="allowed" value="%ALLOWED%" style="width:600px;"/>
  </div>
  <div style="margin-top:10px;">
    <button type="submit">Save</button>
    <a href="/grok/ui" style="margin-left:10px;">Back to Assistant</a>
  </div>
</form>
</body>
</html>'''

UI_HTML = '''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Grok Assistant</title></head>
<body>
  <h1>Grok Assistant</h1>
  <div><a href="/grok/config">Settings</a></div>
  <input type="hidden" id="grok_session_id" value="%SESSION_ID%"/>
  <div>
    <button id="grok_start_stop" type="button">Start Voice</button>
    <label><input type="checkbox" id="grok_execute"/> Allow actions</label>
  </div>
  <div>
    <input type="text" id="grok_text" placeholder="Type and press Send"/>
    <button id="grok_send" type="button">Send</button>
  </div>
  <hr/>
  <ul id="grok_messages" style="max-height:300px;overflow:auto;"></ul>
<script>
(function(){
  function appendMessage(role, text) {
    var ul = document.getElementById("grok_messages");
    var li = document.createElement("li");
    li.textContent = role.toUpperCase() + ": " + text;
    ul.appendChild(li);
    ul.scrollTop = ul.scrollHeight;
  }
  function unpack(data) {
    if (!data) return null;
    if (data.error) {
      var msg = (data.error.data && data.error.data.message) || data.error.message || "Unknown server error";
      return { reply: "Server error: " + msg, results: [] };
    }
    if (typeof data.result !== "undefined") {
      return data.result;
    }
    return data;
  }
  async function sendToServer(message, execute) {
    const sessionId = document.getElementById("grok_session_id").value;
    try {
      const res = await fetch("/grok/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({jsonrpc: "2.0", method: "call", params: {session_id: sessionId, message: message, execute: !!execute}})
      });
      const data = await res.json();
      const payload = unpack(data) || { reply: "No payload", results: [] };
      if (typeof payload.reply === "undefined") {
        return { reply: "No reply from server", results: [] };
      }
      return payload;
    } catch(e) {
      return {reply: "RPC error: " + e, results: []};
    }
  }
  function speak(text) {
    if (!window.speechSynthesis) return;
    var utter = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utter);
  }
  var btn = document.getElementById("grok_send");
  var inp = document.getElementById("grok_text");
  var chk = document.getElementById("grok_execute");
  var startBtn = document.getElementById("grok_start_stop");
  if (btn && inp) {
    btn.addEventListener("click", async function(){
      var msg = (inp.value || "").trim();
      if (!msg) return;
      appendMessage("user", msg);
      inp.value = "";
      var res = await sendToServer(msg, chk && chk.checked);
      appendMessage("assistant", res.reply || "");
      if (res.results && res.results.length) {
        appendMessage("assistant", "Actions: " + res.results.join(" | "));
      }
      speak(res.reply || "");
    });
    inp.addEventListener("keydown", function(ev){
      if (ev.key === "Enter") btn.click();
    });
  }
  var recognizing = false;
  var recognition = null;
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) {
    recognition = new SR();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = async function(event){
      for (var i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          var transcript = event.results[i][0].transcript;
          appendMessage("user", transcript);
          var res = await sendToServer(transcript, chk && chk.checked);
          appendMessage("assistant", res.reply || "");
          if (res.results && res.results.length) {
            appendMessage("assistant", "Actions: " + res.results.join(" | "));
          }
          speak(res.reply || "");
        }
      }
    };
    recognition.onerror = function(e){ console.warn("Speech recognition error", e); };
  }
  if (startBtn) {
    startBtn.addEventListener("click", function(){
      if (!recognition) {
        alert("SpeechRecognition not supported in this browser.");
        return;
      }
      if (!recognizing) {
        recognition.start(); recognizing = true; startBtn.textContent = "Stop Voice";
      } else {
        recognition.stop(); recognizing = false; startBtn.textContent = "Start Voice";
      }
    });
  }
})();
</script>
</body>
</html>'''

class GrokAssistantController(http.Controller):

    @http.route('/grok/config', type='http', auth='user', website=False, csrf=False)
    def grok_config(self, **kw):
        provider = (_get_param('grok_odoo_assistant.provider', 'xai') or 'xai').lower()
        sel_xai = 'selected' if provider == 'xai' else ''
        sel_groq = 'selected' if provider == 'groq' else ''
        sel_custom = 'selected' if provider == 'custom' else ''
        html = CONFIG_HTML.replace('%SEL_XAI%', sel_xai).replace('%SEL_GROQ%', sel_groq).replace('%SEL_CUSTOM%', sel_custom)
        html = html.replace('%ENDPOINT%', escape(_get_param('grok_odoo_assistant.endpoint_url', '')))
        html = html.replace('%API_KEY%', escape(_get_param('grok_odoo_assistant.api_key', '')))
        html = html.replace('%MODEL%', escape(_get_param('grok_odoo_assistant.model', 'grok-4-latest')))
        html = html.replace('%TEMP%', escape(_get_param('grok_odoo_assistant.temperature', '0.0')))
        html = html.replace('%ALLOWED%', escape(_get_param('grok_odoo_assistant.allowed_models', 'res.partner,sale.order,sale.order.line')))
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/grok/config/save', type='http', auth='user', methods=['POST'], website=False, csrf=False)
    def grok_config_save(self, **post):
        _set_param('grok_odoo_assistant.provider', (post.get('provider') or 'xai').lower())
        _set_param('grok_odoo_assistant.endpoint_url', post.get('endpoint_url', ''))
        _set_param('grok_odoo_assistant.api_key', post.get('api_key', ''))
        _set_param('grok_odoo_assistant.model', post.get('model', 'grok-4-latest'))
        _set_param('grok_odoo_assistant.temperature', post.get('temperature', '0.0'))
        _set_param('grok_odoo_assistant.allowed_models', post.get('allowed', 'res.partner,sale.order,sale.order.line'))
        return request.redirect('/grok/ui')

    @http.route('/grok/ping', type='http', auth='user', website=False, csrf=False)
    def grok_ping(self, **kw):
        return "OK"

    @http.route('/grok/ui', type='http', auth='user', website=False, csrf=False)
    def grok_ui(self, **kw):
        session = request.env['grok.assistant.session'].sudo().create({})
        html = UI_HTML.replace("%SESSION_ID%", str(session.id))
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/grok/chat', type='json', auth='user', csrf=False)
    def grok_chat(self, session_id=None, message="", execute=False):
        Session = request.env['grok.assistant.session'].sudo()
        session = Session.browse(int(session_id or 0))
        if not session.exists():
            session = Session.create({})
        request.env['grok.assistant.message'].sudo().create({
            'session_id': session.id,
            'role': 'user',
            'content': message or "",
        })
        assistant_text = session._call_llm(message or "")
        request.env['grok.assistant.message'].sudo().create({
            'session_id': session.id,
            'role': 'assistant',
            'content': assistant_text or "",
        })
        results = []
        if execute:
            results = session._maybe_execute_command(assistant_text)
        return {"reply": assistant_text, "results": results}
