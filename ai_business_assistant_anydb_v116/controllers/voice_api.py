# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging
import requests

_logger = logging.getLogger(__name__)

class VoiceChatController(http.Controller):
    @http.route(['/ai_voice/chat'], type='json', auth='user', methods=['POST'], csrf=False)
    def ai_voice_chat(self, **payload):
        params = payload.get("params") or payload
        text = (params.get("text") if isinstance(params, dict) else "") or ""
        ICP = request.env['ir.config_parameter'].sudo()
        endpoint = ICP.get_param('ai_voice.chat_endpoint', default='')
        api_key = ICP.get_param('ai_voice.api_key', default='')
        api_header_name = ICP.get_param('ai_voice.api_header_name', default='Authorization')
        model_hint = ICP.get_param('ai_voice.model_hint', default='gpt-4o-mini')
        try:
            temperature = float(ICP.get_param('ai_voice.temperature', default='0.7'))
        except Exception:
            temperature = 0.7

        if endpoint:
            try:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers[api_header_name or 'Authorization'] = "Bearer %s" % api_key
                body = {
                    "messages": [{"role": "user", "content": text}],
                    "model": model_hint,
                    "temperature": temperature,
                }
                resp = requests.post(endpoint, headers=headers, data=json.dumps(body), timeout=60)
                resp.raise_for_status()
                data = resp.json()
                reply = None
                if isinstance(data, dict):
                    try:
                        reply = data["choices"][0]["message"]["content"]
                    except Exception:
                        reply = data.get("reply") or json.dumps(data)[:2000]
                else:
                    reply = str(data)[:2000]
                return {"reply": reply}
            except Exception as e:
                _logger.exception("Voice forward error: %s", e)
                return {"reply": "(assistant offline) I received: %s" % text}
        return {"reply": "You said: %s. (Configure 'ai_voice.chat_endpoint' in System Parameters.)" % text}
