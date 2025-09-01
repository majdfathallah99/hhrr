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
    <button id="voice" type="button">Start Voice</button>
    <label><input type="checkbox" id="exec"/> Allow actions</label>
  </div>
  <div>
    <input type="text" id="t" placeholder="Type and press Send"/>
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
  var btn=document.getElementById('s'), t=document.getElementById('t'), chk=document.getElementById('exec'), sid=document.getElementById('sid'), voice=document.getElementById('voice');
  btn.addEventListener('click', async function(){
    var m=(t.value||'').trim(); if(!m) return; add('user', m); t.value='';
    try{
      var txt = await postForm('/grok/chat_http', {message:m, session_id:sid.value, execute: chk && chk.checked ? '1':'0'});
      add('assistant', txt);
      if (window.speechSynthesis){ var u=new SpeechSynthesisUtterance(txt); speechSynthesis.speak(u); }
    }catch(e){ add('assistant', 'HTTP error: '+e); }
  });
  t.addEventListener('keydown', function(ev){ if(ev.key==='Enter') btn.click(); });

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recognizing=false, recognition=null;
  if (SR){ recognition = new SR(); recognition.lang='en-US'; recognition.continuous=true; recognition.interimResults=false;
    recognition.onresult = async function(event){
      for (var i=event.resultIndex;i<event.results.length;i++){
        if (event.results[i].isFinal){
          var transcript = event.results[i][0].transcript;
          add('user', transcript);
          try{
            var txt = await postForm('/grok/chat_http', {message:transcript, session_id:sid.value, execute: chk && chk.checked ? '1':'0'});
            add('assistant', txt);
            if (window.speechSynthesis){ var u=new SpeechSynthesisUtterance(txt); speechSynthesis.speak(u); }
          }catch(e){ add('assistant','HTTP error: '+e); }
        }
      }
    };
    recognition.onerror = function(e){ console.warn('Speech recognition error', e); };
  }
  voice.addEventListener('click', function(){
    if (!recognition){ alert('SpeechRecognition not supported in this browser.'); return; }
    if (!recognizing){ recognition.start(); recognizing=true; voice.textContent='Stop Voice'; }
    else { recognition.stop(); recognizing=false; voice.textContent='Start Voice'; }
  });
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
            full = assistant_text + "\nActions: " + " | ".join(results)
        return request.make_response(full, headers=[('Content-Type','text/plain; charset=utf-8')])
