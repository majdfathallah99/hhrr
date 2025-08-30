# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_voice_chat_endpoint = fields.Char(
        "Voice Chat Endpoint",
        config_parameter='ai_voice.chat_endpoint',
        help="OpenAI-compatible chat endpoint or your own."
    )
    ai_voice_api_key = fields.Char("Voice Chat API Key", config_parameter='ai_voice.api_key')
    ai_voice_api_header_name = fields.Char("API Header Name", config_parameter='ai_voice.api_header_name', default="Authorization")
    ai_voice_model_hint = fields.Char("Model Hint", config_parameter='ai_voice.model_hint', default="gpt-4o-mini")
    ai_voice_temperature = fields.Float("Temperature", config_parameter='ai_voice.temperature', default=0.7)
