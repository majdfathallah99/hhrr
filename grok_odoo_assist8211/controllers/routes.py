# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

def _get(key, default=''):
    return request.env['ir.config_parameter'].sudo().get_param(key, default)

class GrokAssistantController(http.Controller):
    @http.route('/grok', type='http', auth='user', csrf=False)
    def index(self, **kw):
        return request.make_response(INDEX_HTML, headers=[('Content-Type','text/html; charset=utf-8')])

    @http.route('/grok/send', type='json', auth='user')
    def send(self, text="", execute=False, **kw):
        session = request.env['grok.assistant.session'].sudo().search([('user_id','=',request.env.user.id)], limit=1)
        if not session:
            session = request.env['grok.assistant.session'].sudo().create({"user_id": request.env.user.id, "execute": bool(execute)})
        else:
            session.sudo().write({"execute": bool(execute)})
        reply, results = request.env['grok.assistant.message'].sudo().send_user_message(session, text or "")
        return {"reply": reply, "results": results, "execute": session.execute}

INDEX_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>Grok Assistant</title>
<link rel="stylesheet" href="/grok/static/app.css"/>
</head>
<body>
<div class="wrap">
  <h2>🎤 بدء التحدث  ✅ تنفيذ الإجراءات    الإعدادات</h2>
  <div class="row">
    <input id="text" placeholder="اكتب رسالتك هنا ثم اضغط إرسال" />
    <button id="send">📨 إرسال</button>
  </div>
  <div class="tips">📌 نماذج سريعة (SO/PO/منتجات)</div>
  <ul id="log"></ul>
</div>
<script src="/grok/static/app.js"></script>
</body>
</html>"""
