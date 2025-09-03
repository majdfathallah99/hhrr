
# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class GptAssistantController(http.Controller):

    @http.route('/gpt5/chat', type='json', auth='user', csrf=False)
    def chat(self, thread_id=None, prompt=None):
        env = request.env
        if not thread_id or not prompt:
            return {'ok': False, 'error': 'Missing thread_id or prompt'}
        thread = env['gpt.assistant.thread'].browse(int(thread_id))
        if not thread.exists():
            return {'ok': False, 'error': 'Thread not found'}
        res = thread.chat(prompt)
        return {'ok': True, 'reply': res.get('reply')}
