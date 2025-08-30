
import json
from odoo import http
from odoo.http import request

class AIVoiceSignaling(http.Controller):

    @http.route(['/ai_voice/config'], type='json', auth='user')
    def get_config(self):
        ICP = request.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('ai_voice.enabled', 'True') == 'True'
        stun = ICP.get_param('ai_voice.stun_servers', 'stun:stun.l.google.com:19302')
        turn_json = ICP.get_param('ai_voice.turn_servers', '[]')
        try:
            turn = json.loads(turn_json) if turn_json else []
        except Exception:
            turn = []
        return {
            'enabled': enabled,
            'iceServers': [{'urls': [u.strip() for u in stun.split(',') if u.strip()]}] + turn,
        }

    @http.route(['/ai_voice/subscribe'], type='json', auth='user')
    def subscribe(self, room_key):
        # Use Odoo bus to subscribe: the webclient already polls; we just return the channel name
        return {
            'channel': self._channel_name(room_key),
        }

    @http.route(['/ai_voice/signal'], type='json', auth='user')
    def signal(self, room_key, payload):
        # Broadcast a signaling payload to all subscribers of the room
        channel = self._channel_name(room_key)
        request.env['bus.bus']._sendone(channel, {
            't': 'ai_voice',
            'room': room_key,
            'payload': payload,
            'sender': request.env.user.id,
            'sender_name': request.env.user.name,
        })
        return {'ok': True}

    def _channel_name(self, room_key):
        # Namespace by DB and module key
        db = request.env.cr.dbname
        return (db, 'ai_voice', room_key)
