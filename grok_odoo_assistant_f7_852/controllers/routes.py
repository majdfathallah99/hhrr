# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from markupsafe import escape

def _get(key, default=''):
    return request.env['ir.config_parameter'].sudo().get_param(key, default)

def _set(key, val):
    request.env['ir.config_parameter'].sudo().set_param(key, val or '')

CONFIG_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Grok Settings</title></head>
<body>
<h1>Grok Settings</h1>
<form method="post" action="/grok/config/save">
  <table border="0" cellpadding="4" cellspacing="0">
    <tr>
      <td>Provider</td>
      <td>
        <select name="provider">
          <option value="xai" %SEL_XAI%>x.ai (Grok)</option>
          <option value="groq" %SEL_GROQ%>Groq (OpenAI-compatible)</option>
          <option value="custom" %SEL_CUSTOM%>Custom Endpoint</option>
        </select>
      </td>
    </tr>
    <tr><td>Endpoint URL (for Custom)</td><td><input type="text" name="endpoint_url" value="%ENDPOINT%"/></td></tr>
    <tr><td>API Key</td><td><input type="password" name="api_key" value="%API_KEY%"/></td></tr>
    <tr><td>Model</td><td><input type="text" name="model" value="%MODEL%" placeholder="grok-4-latest or llama-3.1-8b-instant"/></td></tr>
    <tr><td>Temperature</td><td><input type="number" name="temperature" step="0.1" value="%TEMP%"/></td></tr>
    <tr><td>Allowed Odoo Models</td><td><input type="text" name="allowed" value="%ALLOWED%"/></td></tr>
    <tr><td colspan="2"><button type="submit">💾 حفظ</button> &nbsp; <a href="/grok/ui">⬅ الرجوع للمساعد</a></td></tr>
  </table>
</form>
</body></html>"""

UI_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>🤖 Grok Assistant</title></head>
<body>
  <h1>🤖 مساعد أودو (Grok) — عربي فقط</h1>
  <input type="hidden" id="sid" value="%SESSION_ID%"/>
  <table border="0" cellpadding="4" cellspacing="0">
    <tr>
      <td>
        <button id="voice" type="button" onclick="return (window.Grok && Grok.onVoiceClick && Grok.onVoiceClick()) || false">🎤 بدء التحدث</button>
        <label style="margin-inline-start:8px">🌐 <select id="lang"><option value="ar-SA">العربية</option><option value="en-US">English</option></select></label>
        <label style="margin-inline-start:8px"><input type="checkbox" id="tts" checked/> 🔊 نطق الردود</label>
        <label><input type="checkbox" id="exec"/> ✅ تنفيذ الإجراءات</label>
        &nbsp;&nbsp; <a href="/grok/config">الإعدادات</a>
      </td>
    </tr>
    <tr>
      <td>
        <input type="text" id="t" size="70" placeholder="اكتب رسالتك هنا ثم اضغط إرسال"/>
        <button id="s" type="button" onclick="return (window.Grok && Grok.onSendClick && Grok.onSendClick()) || false">📨 إرسال</button>
      </td>
    </tr>
  </table>
  <hr/>
  <details>
    <summary>📌 نماذج سريعة (SO/PO/منتجات)</summary>
    <pre>
- منتج جديد:
  الاسم=كيبورد، الكود=KB-001، سعر البيع=120، التكلفة=80
- أمر بيع مع بنود:
  للعميل "شركة الاختبار" ببنود: KB-001*2|كيبورد*1@120
- أمر شراء مع بنود:
  للمورد "مورد الاختبار" ببنود: KB-001*5@70
    </pre>
  </details>
  <hr/>
  <ul id="log"></ul>
  <script defer src="/grok/app.js"></script>
</body></html>"""

APP_JS = """(function(){
  function byId(id){ return document.getElementById(id); }
  function add(role, text){
    var ul=byId('log'); var li=document.createElement('li');
    li.textContent=role.toUpperCase()+': '+text; ul.appendChild(li);
    if (ul.children.length>200){ ul.removeChild(ul.firstChild); }
  }
  async function postForm(url, data){
    var kv = []; for (var k in data){ if (Object.prototype.hasOwnProperty.call(data,k)) kv.push(encodeURIComponent(k)+'='+encodeURIComponent(data[k])); }
    var body = kv.join('&');
    var res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: body});
    return res.text();
  }
  function isFemaleName(n){
    n = (n||'').toLowerCase();
    return /female|hoda|zariyah|salma|amira|mona|layla|laila|noura|nora|zeina|zeinab|rana|dina|susan|sara|farah|ruqayya|asmaa|asma|noor|haneen|hanan|sahar|luna|sofia|sofiya|huda|zein/.test(n);
  }
  function scoreVoice(v){
    var s=0;
    if (!v) return -1;
    if ((v.lang||'').toLowerCase()==='ar-sa') s+=8;
    if ((v.lang||'').toLowerCase().indexOf('ar')===0) s+=5;
    if (isFemaleName(v.name)) s+=4;
    if (/google|microsoft|apple/.test((v.name||'').toLowerCase())) s+=1;
    return s;
  }
  function pickFemaleVoice(){
    if (!window.speechSynthesis) return null;
    var voices = window.speechSynthesis.getVoices();
    if (!voices || !voices.length) return null;
    var best = null, bestScore=-1;
    for (var i=0;i<voices.length;i++){
      var sc = scoreVoice(voices[i]);
      if (sc>bestScore){ best=voices[i]; bestScore=sc; }
    }
    return best;
  }
  function speak(text){
    if (!window.speechSynthesis) return;
    var u = new SpeechSynthesisUtterance(text);
    u.lang = 'ar-SA';
    var v = pickFemaleVoice();
    if (v) u.voice = v;
    window.speechSynthesis.speak(u);
  }
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recognition=null, recognizing=false;
  function setupSR(){
    if (!SR) return;
    if (recognition) try{ recognition.abort(); }catch(e){}
    recognition = new SR();
    recognition.lang = 'ar-SA';
      try{var __sel=document.getElementById('lang'); if(__sel&&__sel.value){ recognition.lang = __sel.value; }}catch(e){}
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = function(event){
      for (var i=event.resultIndex;i<event.results.length;i++){
        if (event.results[i].isFinal){
          var transcript = event.results[i][0].transcript;
          add('user', transcript);
          sendText(transcript);
        }
      }
    };
    recognition.onerror = function(e){ add('assistant', '🚫 مشكلة في الميكروفون أو الإذن: '+e.error); };
  }
  async function sendText(msg){
    var sid = byId('sid').value;
    var submitMsg = 'يرجى الرد باللغة العربية فقط:\n' + msg;
    try{
      var txt = await postForm('/grok/chat_http', {message: submitMsg, session_id: sid, execute: '0'});
      add('assistant', txt);
      speak(txt);
    }catch(e){ add('assistant', 'HTTP error: '+e); }
  }
  function bindUI(){
    var btn = byId('s'); var t = byId('t'); var voiceBtn = byId('voice');
    if (btn) btn.addEventListener('click', function(){
      var m=(t.value||'').trim(); if(!m) return; add('user', m); t.value=''; sendText(m);
    });
    if (t) t.addEventListener('keydown', function(ev){ if(ev.key==='Enter') byId('s').click(); });
    if (voiceBtn) voiceBtn.addEventListener('click', function(){
      if (!SR){ alert('متصفحك لا يدعم التعرف على الصوت.'); return; }
      if (!recognizing){ 
        if (!recognition) setupSR();
        recognition.start(); recognizing=true; voiceBtn.textContent='■ إيقاف التحدث';
      } else {
        recognition.stop(); recognizing=false; voiceBtn.textContent='🎤 بدء التحدث';
      }
    });
  }
  function init(){
    bindUI();
    if (window.speechSynthesis){
      var hasAr = (window.speechSynthesis.getVoices()||[]).some(function(v){return (v.lang||'').toLowerCase().indexOf('ar')===0;});
      if (!hasAr){
        add('assistant','ℹ لا توجد أصوات عربية على هذا الجهاز. أضِف صوتًا عربيًا من إعدادات النظام ثم أعد فتح الصفحة.');
      }
    }
    if (SR) setupSR();
  }
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

// === Bilingual Voice Add-on (non-invasive) ===
;(function(){
  function isArabicText(s){ return /[\u0600-\u06FF]/.test(s||''); }
  function pickVoiceByLang(lang){
    try{
      if (!window.speechSynthesis) return null;
      var vs = window.speechSynthesis.getVoices()||[];
      var best=null,score=-1, l=(lang||'').toLowerCase();
      for (var i=0;i<vs.length;i++){
        var v=vs[i], vl=(v.lang||'').toLowerCase(); var sc=0;
        if (l && vl.indexOf(l.slice(0,2))===0) sc+=10;
        if (/female|woman|ar-|en-/.test((v.name||'').toLowerCase())) sc+=1;
        if (sc>score){ score=sc; best=v; }
      }
      return best;
    }catch(e){ return null; }
  }
  try{
    if (typeof speak === 'function'){
      var __oldSpeak = speak;
      speak = function(text){
        var ttsEl = document.getElementById('tts');
        if (ttsEl && !ttsEl.checked) return;
        try{
          if (!window.speechSynthesis){ __oldSpeak(text); return; }
          var sel = document.getElementById('lang');
          var lang = (sel && sel.value) || (isArabicText(text) ? 'ar-SA' : 'en-US');
          var u = new SpeechSynthesisUtterance(text);
          u.lang = lang;
          var v = pickVoiceByLang(lang);
          if (!v && typeof pickFemaleVoice === 'function') v = pickFemaleVoice();
          if (v) u.voice = v;
          window.speechSynthesis.speak(u);
        }catch(e){
          try{ __oldSpeak(text); }catch(_){}
        }
      };
    }
  }catch(e){ /* no-op */ }

  // Update SR language on selector change, if SR exists
  try{
    var langSel = document.getElementById('lang');
    if (langSel){
      langSel.addEventListener('change', function(){
        try{ if (window.SR && window.SR.recognition){ window.SR.recognition.lang = langSel.value; } }catch(_){}
        try{ localStorage.setItem('grok_lang', langSel.value); }catch(_){}
      });
      try{
        var saved = localStorage.getItem('grok_lang'); if (saved) langSel.value = saved;
      }catch(_){}
    }
  }catch(e){}
})(); // === end add-on ===
"""

class GrokAssistantArOnly(http.Controller):
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
                .replace('%ALLOWED%', escape(_get('grok_odoo_assistant.allowed_models','res.partner,product.template,product.product,sale.order,sale.order.line,purchase.order,purchase.order.line')))
            )
        return request.make_response(html, headers=[('Content-Type','text/html; charset=utf-8')])

    @http.route('/grok/config/save', type='http', methods=['POST'], auth='user', csrf=False)
    def save(self, **post):
        _set('grok_odoo_assistant.provider', (post.get('provider') or 'xai').lower())
        _set('grok_odoo_assistant.endpoint_url', post.get('endpoint_url',''))
        _set('grok_odoo_assistant.api_key', post.get('api_key',''))
        _set('grok_odoo_assistant.model', post.get('model','grok-4-latest'))
        _set('grok_odoo_assistant.temperature', post.get('temperature','0.0'))
        _set('grok_odoo_assistant.allowed_models', post.get('allowed','res.partner,product.template,product.product,sale.order,sale.order.line,purchase.order,purchase.order.line'))
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
        request.env['grok.assistant.message'].sudo().create({ 'session_id': session.id, 'role': 'user', 'content': message })
        try:
            assistant_text = session._call_llm(message)
        except Exception as e:
            assistant_text = str(e) or "حدث خطأ غير متوقع عند الاتصال بالمزوّد."
        if not assistant_text:
            assistant_text = "لم يصلني رد. رجاءً تحقق من الإعدادات (Provider/Model/API Key) ثم أعد المحاولة."
        request.env['grok.assistant.message'].sudo().create({ 'session_id': session.id, 'role': 'assistant', 'content': assistant_text })
        results = []
        if execute:
            results = session._maybe_execute_command(assistant_text)
        full = assistant_text
        if results:
            full = assistant_text + "\nActions: " + " | ".join(results)
        return request.make_response(full, headers=[('Content-Type','text/plain; charset=utf-8')])

    @http.route('/grok/app.js', type='http', auth='user', csrf=False)
    def app_js(self, **kw):
        return request.make_response(APP_JS, headers=[('Content-Type','application/javascript; charset=utf-8')])
