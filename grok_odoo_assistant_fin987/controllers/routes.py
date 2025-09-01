# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from markupsafe import escape

def _get(key, default=''):
    return request.env['ir.config_parameter'].sudo().get_param(key, default)

def _set(key, val):
    request.env['ir.config_parameter'].sudo().set_param(key, val or '')

CONFIG_HTML = '<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>Grok Settings</title></head>\n<body>\n<h1>Grok Settings</h1>\n<form method="post" action="/grok/config/save">\n  <table border="0" cellpadding="4" cellspacing="0">\n    <tr>\n      <td>Provider</td>\n      <td>\n        <select name="provider">\n          <option value="xai" %SEL_XAI%>x.ai (Grok)</option>\n          <option value="groq" %SEL_GROQ%>Groq (OpenAI-compatible)</option>\n          <option value="custom" %SEL_CUSTOM%>Custom Endpoint</option>\n        </select>\n      </td>\n    </tr>\n    <tr><td>Endpoint URL (for Custom)</td><td><input type="text" name="endpoint_url" value="%ENDPOINT%"/></td></tr>\n    <tr><td>API Key</td><td><input type="password" name="api_key" value="%API_KEY%"/></td></tr>\n    <tr><td>Model</td><td><input type="text" name="model" value="%MODEL%" placeholder="grok-4-latest or llama-3.1-8b-instant"/></td></tr>\n    <tr><td>Temperature</td><td><input type="number" name="temperature" step="0.1" value="%TEMP%"/></td></tr>\n    <tr><td>Allowed Odoo Models</td><td><input type="text" name="allowed" value="%ALLOWED%"/></td></tr>\n    <tr><td colspan="2"><button type="submit">💾 حفظ</button> &nbsp; <a href="/grok/ui">⬅ الرجوع للمساعد</a></td></tr>\n  </table>\n</form>\n</body></html>'
UI_HTML = '<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>🤖 Grok Assistant</title></head>\n<body>\n  <h1>🤖 مساعد أودو (Grok)</h1>\n  <table border="0" cellpadding="4" cellspacing="0">\n    <tr>\n      <td><b>🔧 الإعدادات:</b> <a href="/grok/config">فتح صفحة الإعدادات</a></td>\n    </tr>\n    <tr>\n      <td><b>🌐 اللغة:</b>\n        <select id="lang">\n          <option value="ar-SA" selected>العربية (السعودية)</option>\n          <option value="ar-EG">العربية (مصر)</option>\n          <option value="en-US">English (US)</option>\n        </select>\n      </td>\n    </tr>\n    <tr>\n      <td>\n        <button id="voice" type="button">🎤 بدء التحدث</button>\n        <label><input type="checkbox" id="exec"/> ✅ تنفيذ الإجراءات</label>\n      </td>\n    </tr>\n    <tr>\n      <td>\n        <input type="text" id="t" size="70" placeholder="اكتب رسالتك هنا ثم اضغط إرسال / Type and press Send"/>\n        <button id="s" type="button">📨 إرسال</button>\n      </td>\n    </tr>\n  </table>\n  <hr/>\n  <details>\n    <summary>📌 نماذج سريعة (SO/PO/منتجات)</summary>\n    <pre>\n- منتج جديد:\n  الاسم=كيبورد، الكود=KB-001، سعر البيع=120، التكلفة=80\n- أمر بيع مع بنود:\n  للعميل "شركة الاختبار" ببنود: KB-001*2|كيبورد*1@120\n- أمر شراء مع بنود:\n  للمورد "مورد الاختبار" ببنود: KB-001*5@70\n    </pre>\n  </details>\n  <hr/>\n  <ul id="log"></ul>\n  <script defer src="/grok/app.js"></script>\n</body></html>'
APP_JS = "(function(){\n  function byId(id){ return document.getElementById(id); }\n  function add(role, text){\n    var ul=byId('log'); var li=document.createElement('li');\n    li.textContent=role.toUpperCase()+': '+text; ul.appendChild(li);\n    if (ul.children.length>200){ ul.removeChild(ul.firstChild); }\n  }\n  async function postForm(url, data){\n    var kv = []; for (var k in data){ if (Object.prototype.hasOwnProperty.call(data,k)) kv.push(encodeURIComponent(k)+'='+encodeURIComponent(data[k])); }\n    var body = kv.join('&');\n    var res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: body});\n    return res.text();\n  }\n  function isFemaleName(n){\n    n = (n||'').toLowerCase();\n    return /female|hoda|zariyah|salma|amira|mona|layla|laila|noura|nora|zeina|zeinab|rana|dina|susan|sara|farah|ruqayya|asmaa|asma|noor|haneen|hanan|sahar|luna|sofia|sofiya|huda|zein/.test(n);\n  }\n  function scoreVoice(v, lang){\n    var s=0;\n    if (!v) return -1;\n    if (v.lang && v.lang.toLowerCase().indexOf((lang||'').split('-')[0].toLowerCase())===0) s+=5;\n    if (v.lang === lang) s+=5;\n    if (isFemaleName(v.name)) s+=4;\n    if (/google|microsoft|apple/.test((v.name||'').toLowerCase())) s+=1;\n    return s;\n  }\n  function pickFemaleVoice(lang){\n    if (!window.speechSynthesis) return null;\n    var voices = window.speechSynthesis.getVoices();\n    if (!voices || !voices.length) return null;\n    var best = null, bestScore=-1;\n    for (var i=0;i<voices.length;i++){\n      var sc = scoreVoice(voices[i], lang);\n      if (sc>bestScore){ best=voices[i]; bestScore=sc; }\n    }\n    return best;\n  }\n  function speak(text){\n    if (!window.speechSynthesis) return;\n    var lang = byId('lang').value || 'ar-SA';\n    var u = new SpeechSynthesisUtterance(text);\n    u.lang = lang;\n    var v = pickFemaleVoice(lang);\n    if (v) u.voice = v;\n    window.speechSynthesis.speak(u);\n  }\n  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;\n  var recognition=null, recognizing=false;\n  function setupSR(){\n    if (!SR) return;\n    if (recognition) try{ recognition.abort(); }catch(e){}\n    recognition = new SR();\n    recognition.lang = byId('lang').value || 'ar-SA';\n    recognition.continuous = true;\n    recognition.interimResults = false;\n    recognition.onresult = function(event){\n      for (var i=event.resultIndex;i<event.results.length;i++){\n        if (event.results[i].isFinal){\n          var transcript = event.results[i][0].transcript;\n          add('user', transcript);\n          sendText(transcript);\n        }\n      }\n    };\n    recognition.onerror = function(e){ add('assistant', '🚫 مشكلة في الميكروفون أو الإذن: '+e.error); };\n  }\n  async function sendText(msg){\n    var sid = byId('sid').value;\n    var chk = byId('exec');\n    var lang = byId('lang').value || 'ar-SA';\n    var submitMsg = msg;\n    if (lang && lang.indexOf('ar')===0){\n      submitMsg = 'يرجى الرد باللغة العربية فقط:\\\\n' + msg;\n    }\n    try{\n      var txt = await postForm('/grok/chat_http', {message: submitMsg, session_id: sid, execute: chk && chk.checked ? '1':'0'});\n      add('assistant', txt);\n      speak(txt);\n    }catch(e){ add('assistant', 'HTTP error: '+e); }\n  }\n  function bindUI(){\n    var btn = byId('s'); var t = byId('t'); var voiceBtn = byId('voice');\n    if (btn) btn.addEventListener('click', function(){\n      var m=(t.value||'').trim(); if(!m) return; add('user', m); t.value=''; sendText(m);\n    });\n    if (t) t.addEventListener('keydown', function(ev){ if(ev.key==='Enter') byId('s').click(); });\n    if (byId('lang')) byId('lang').addEventListener('change', function(){ if (recognition){ try{ recognition.stop(); }catch(e){} } setupSR(); });\n    if (voiceBtn) voiceBtn.addEventListener('click', function(){\n      if (!SR){ alert('متصفحك لا يدعم التعرف على الصوت.'); return; }\n      if (!recognizing){ \n        if (!recognition) setupSR();\n        recognition.start(); recognizing=true; voiceBtn.textContent='■ إيقاف التحدث';\n      } else {\n        recognition.stop(); recognizing=false; voiceBtn.textContent='🎤 بدء التحدث';\n      }\n    });\n  }\n  function init(){\n    bindUI();\n    if (window.speechSynthesis){\n      var hasAr = (window.speechSynthesis.getVoices()||[]).some(function(v){return (v.lang||'').toLowerCase().indexOf('ar')===0;});\n      if (!hasAr){\n        add('assistant','ℹ لا توجد أصوات عربية على هذا الجهاز. أضِف صوتًا عربيًا من إعدادات النظام ثم أعد فتح الصفحة.');\n      }\n    }\n    if (SR) setupSR();\n  }\n  if (document.readyState === 'loading'){\n    document.addEventListener('DOMContentLoaded', init);\n  } else {\n    init();\n  }\n})();"

class GrokAssistantFinal2(http.Controller):
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
            return request.make_response(str(e), headers=[('Content-Type','text/plain; charset=utf-8')])
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
