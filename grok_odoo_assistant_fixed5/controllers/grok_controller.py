# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

HTML_PAGE = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Grok Assistant</title>
</head>
<body>
  <h1>Grok Assistant</h1>
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
  async function sendToServer(message, execute) {
    const sessionId = document.getElementById("grok_session_id").value;
    try {
      const res = await fetch("/grok/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({jsonrpc: "2.0", method: "call", params: {session_id: sessionId, message: message, execute: !!execute}})
      });
      const data = await res.json();
      return data.result || {reply: "No result", results: []};
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

    @http.route('/grok/ping', type='http', auth='user', website=False, csrf=False)
    def grok_ping(self, **kw):
        return "OK"

    @http.route('/grok/ui', type='http', auth='user', website=False, csrf=False)
    def grok_ui(self, **kw):
        session = request.env['grok.assistant.session'].sudo().create({})
        html = HTML_PAGE.replace("%SESSION_ID%", str(session.id))
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
        assistant_text = session._call_xai(message or "")
        request.env['grok.assistant.message'].sudo().create({
            'session_id': session.id,
            'role': 'assistant',
            'content': assistant_text or "",
        })
        results = []
        if execute:
            results = session._maybe_execute_command(assistant_text)
        return {"reply": assistant_text, "results": results}
