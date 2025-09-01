# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class GrokAssistantController(http.Controller):

    @http.route('/grok/ui', type='http', auth='user', website=False, csrf=False)
    def grok_ui(self, **kw):
        session = request.env['grok.assistant.session'].sudo().create({})
        return request.render('grok_odoo_assistant.ui', {'session_id': session.id})

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

        return {
            "reply": assistant_text,
            "results": results,
        }