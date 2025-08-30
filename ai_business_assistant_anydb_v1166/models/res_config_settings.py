from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_voice_enabled = fields.Boolean(
        string="Enable Voice Assistant",
        default=True,
        config_parameter="ai_voice.enabled",
    )
    ai_voice_model = fields.Char(
        string="Voice Model",
        default="llama-3.1-8b-instant",
        config_parameter="ai_voice.model",
    )
    ai_voice_base_url = fields.Char(
        string="Voice Base URL",
        default="https://api.groq.com/openai/v1",
        config_parameter="ai_voice.base_url",
    )
    ai_voice_api_key = fields.Char(
        string="Voice API Key",
        config_parameter="ai_voice.api_key",
    )