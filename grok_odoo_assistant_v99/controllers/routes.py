# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from markupsafe import escape

def _get(key, default=''):
    return request.env['ir.config_parameter'].sudo().get_param(key, default)

def _set(key, val):
    request.env['ir.config_parameter'].sudo().set_param(key, val or '')

CONFIG_HTML = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Grok Settings</title></head>
<body>
<h1>Grok Settings</h1>
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
    <input type="text" name="endpoint_url" value="%ENDPOINT%" style="width:600px;"/>
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
    <input type="number" name="temperature" step="0.1" value="%TEMP%"/>
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
</body></html>'''

UI_HTML = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Grok Assistant</title></head>
<body>
  <h1>Grok Assistant</h1>
  <div><a href="/grok/config">Settings</a></div>
  <input type="hidden" id="sid" value="%SESSION_ID%"/>
  <div>
    <label>Language:</label>
    <select id="lang">
      <option value="en-US">English (US)</option>
      <option value="ar-SA" selected>العربية (السعودية)</option>
      <option value="ar-EG">العربية (مصر)</option>
    </select>
    <label style="margin-left:10px;">Voice:</label>
    <select id="voice_select"><option value="">Auto (female if possible)</option></select>
  </div>
  <div style="margin-top:6px;">
    <button id="voice" type="button">Start Voice</button>
    <label><input type="checkbox" id="exec"/> Allow actions</label>
  </div>
  <div style="margin-top:6px;">
    <input type="text" id="t" placeholder="اكتب رسالتك واضغط إرسال / Type and press Send"/>
    <button id="s" type="button">Send</button>
  </div>
  <hr/>
  <ul id="log" style="max-height:300px;overflow:auto;"></ul>
<script>
(function(){
  function add(role, text){
    var ul=document.getElementById('log'); var li=document.createElement('li');
    li.textContent=role.toUpperCase()+': '+text; ul.appendChild(li); ul.scrollTop=ul.scrollHeight;
  }
  async function postForm(url, data){
    const body = new URLSearchParams(data).toString();
    const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body});
    return res.text();
  }

  // ----- TTS Voice handling -----
  var voiceSelect = document.getElementById('voice_select');
  var preferredVoice = null;
  function scoreVoice(v, lang){
    var s = 0;
    if (v.lang && v.lang.toLowerCase().startsWith(lang.toLowerCase().split('-')[0])) s += 5; // same base language
    if (v.lang === lang) s += 5; // exact locale
    var n = (v.name||'').toLowerCase();
    if (/female|hoda|zariyah|salma|amira|mona|layla|laila|noura|nora|zeina|zeinab|rana|dina|susan|sara/.test(n)) s += 3; // likely female
    if (/google/.test(n)) s += 1; // tends to be clearer
    return s;
  }
  function populateVoices(){
    var lang = document.getElementById('lang').value || 'ar-SA';
    var voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
    voiceSelect.innerHTML = '<option value=\"\">Auto (female if possible)</option>';
    var arr = voices.slice().sort(function(a,b){ return scoreVoice(b, lang) - scoreVoice(a, lang); });
    arr.forEach(function(v,i){
      var opt = document.createElement('option');
      opt.value = v.name + '|' + v.lang;
      opt.textContent = v.name + ' (' + v.lang + ')';
      voiceSelect.appendChild(opt);
    });
    preferredVoice = arr.length ? arr[0] : null;
  }
  if (window.speechSynthesis){
    window.speechSynthesis.onvoiceschanged = populateVoices;
    populateVoices();
  }

  function speak(text){
    if (!window.speechSynthesis) return;
    var lang = document.getElementById('lang').value || 'ar-SA';
    var choice = voiceSelect.value;
    var u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    if (choice){
      var parts = choice.split('|');
      var name = parts[0], vlang = parts[1];
      var v = window.speechSynthesis.getVoices().find(function(x){ return x.name===name && x.lang===vlang; });
      if (v) u.voice = v;
    } else if (preferredVoice){
      u.voice = preferredVoice;
    }
    window.speechSynthesis.speak(u);
  }

  // ----- STT + chat flow -----
  var btn=document.getElementById('s'), t=document.getElementById('t'), chk=document.getElementById('exec'), sid=document.getElementById('sid'), voiceBtn=document.getElementById('voice');
  async function sendText(msg){
    var lang = document.getElementById('lang').value || 'ar-SA';
    // If Arabic selected, politely ask model to reply in Arabic.
    if (lang && lang.startsWith('ar')){
      msg = 'يرجى الرد باللغة العربية فقط:\n' + msg;
    }
    try{
      var txt = await postForm('/grok/chat_http', {message:msg, session_id:sid.value, execute: chk && chk.checked ? '1':'0'});
      add('assistant', txt);
      speak(txt);
    }catch(e){ add('assistant','HTTP error: '+e); }
  }
  btn.addEventListener('click', async function(){
    var m=(t.value||'').trim(); if(!m) return; add('user', m); t.value='';
    sendText(m);
  });
  t.addEventListener('keydown', function(ev){ if(ev.key==='Enter') btn.click(); });

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recognizing=false, recognition=null;
  function setupSR(){
    if (!SR) return;
    if (recognition) try{ recognition.abort(); }catch(e){}
    recognition = new SR();
    recognition.lang = document.getElementById('lang').value || 'ar-SA';
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = async function(event){
      for (var i=event.resultIndex;i<event.results.length;i++){
        if (event.results[i].isFinal){
          var transcript = event.results[i][0].transcript;
          add('user', transcript);
          sendText(transcript);
        }
      }
    };
    recognition.onerror = function(e){ console.warn('Speech recognition error', e); };
  }
  if (SR) setupSR();
  document.getElementById('lang').addEventListener('change', function(){
    setupSR(); // re-init with new language
  });

  if (voiceBtn){
    voiceBtn.addEventListener('click', function(){
      if (!recognition){ alert('SpeechRecognition not supported in this browser.'); return; }
      if (!recognizing){ recognition.start(); recognizing=true; voiceBtn.textContent='Stop Voice'; }
      else { recognition.stop(); recognizing=false; voiceBtn.textContent='Start Voice'; }
    });
  }
})();
</script>
</body></html>'''

class GrokAssistantFinal(http.Controller):
    @http.route('/grok/ping', type='http', auth='user', csrf=False)
    def ping(self, **kw):
        return "OK"

    @http.route('/grok/config', type='http', auth='user', csrf=False)
    def config(self, **kw):
        prov = (_get('grok_odoo_assistant.provider', 'xai') or 'xai').lower()
        html = (CONFIG_HTML
                .replace('%SEL_XAI%', 'selected' if prov=='xai' else '')
                .replace('%SEL_GROQ%', 'selected' if prov=='groq' else '')
                .replace('%SEL_CUSTOM%', 'selected' if prov=='custom' else '')
                .replace('%ENDPOINT%', escape(_get('grok_odoo_assistant.endpoint_url','')))
                .replace('%API_KEY%', escape(_get('grok_odoo_assistant.api_key','')))
                .replace('%MODEL%', escape(_get('grok_odoo_assistant.model','grok-4-latest')))
                .replace('%TEMP%', escape(_get('grok_odoo_assistant.temperature','0.0')))
                .replace('%ALLOWED%', escape(_get('grok_odoo_assistant.allowed_models','res.partner,sale.order,sale.order.line')))
               )
        return request.make_response(html, headers=[('Content-Type','text/html; charset=utf-8')])

    @http.route('/grok/config/save', type='http', methods=['POST'], auth='user', csrf=False)
    def save(self, **post):
        _set('grok_odoo_assistant.provider', (post.get('provider') or 'xai').lower())
        _set('grok_odoo_assistant.endpoint_url', post.get('endpoint_url',''))
        _set('grok_odoo_assistant.api_key', post.get('api_key',''))
        _set('grok_odoo_assistant.model', post.get('model','grok-4-latest'))
        _set('grok_odoo_assistant.temperature', post.get('temperature','0.0'))
        _set('grok_odoo_assistant.allowed_models', post.get('allowed','res.partner,sale.order,sale.order.line'))
        return request.redirect('/grok/ui')

    @http.route('/grok/ui', type='http', auth='user', csrf=False)
    def ui(self, **kw):
        session = request.env['grok.assistant.session'].sudo().create({})
        html = UI_HTML.replace('%SESSION_ID%', str(session.id))
        return request.make_response(html, headers=[('Content-Type','text/html; charset=utf-8')])

    @http.route('/grok/chat_http', type='http', methods=['POST'], auth='user', csrf=False)
    def chat_http(self, **post):
        sid = int(post.get('session_id') or 0)
        message = post.get('message') or ''
        execute = (post.get('execute') == '1')
        Session = request.env['grok.assistant.session'].sudo()
        session = Session.browse(sid)
        if not session.exists():
            session = Session.create({})
        request.env['grok.assistant.message'].sudo().create({'session_id': session.id, 'role': 'user', 'content': message})
        try:
            assistant_text = session._call_llm(message)
        except Exception as e:
            return request.make_response(str(e), headers=[('Content-Type','text/plain; charset=utf-8')])
        request.env['grok.assistant.message'].sudo().create({'session_id': session.id, 'role': 'assistant', 'content': assistant_text})
        results = []
        if execute:
            results = session._maybe_execute_command(assistant_text)
        full = assistant_text
        if results:
            full = assistant_text + "\\nActions: " + " | ".join(results)
        return request.make_response(full, headers=[('Content-Type','text/plain; charset=utf-8')])
