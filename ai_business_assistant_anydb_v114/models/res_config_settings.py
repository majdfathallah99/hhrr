
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_enabled = fields.Boolean(string="Enable AI Assistant", default=True, config_parameter="ai_business_assistant.ai_enabled")
    ai_provider = fields.Selection([("openai", "OpenAI-compatible (OpenAI, Groq, Ollama)")], string="AI Provider", default="openai", config_parameter="ai_business_assistant.ai_provider")
    ai_model = fields.Char(string="Model name", default="llama-3.1-8b-instant", config_parameter="ai_business_assistant.ai_model")
    ai_api_key = fields.Char(string="API Key", config_parameter="ai_business_assistant.ai_api_key")
    ai_base_url = fields.Char(string="Base URL", default="https://api.groq.com/openai/v1", config_parameter="ai_business_assistant.ai_base_url")
    ai_superuser_mode = fields.Boolean(string="Superuser mode (sudo for tools)", default=False, config_parameter="ai_business_assistant.ai_superuser_mode")
