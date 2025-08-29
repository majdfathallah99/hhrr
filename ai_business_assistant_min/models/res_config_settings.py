
from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_enabled = fields.Boolean(string="Enable AI Assistant", default=True, config_parameter="ai_business_assistant.ai_enabled")
    ai_provider = fields.Selection([
        ("openai", "OpenAI (Chat Completions)"),
        ("azure_openai", "Azure OpenAI (Chat Completions)"),
        ("ollama", "Ollama (local)")
    ], string="AI Provider", default="openai", config_parameter="ai_business_assistant.ai_provider")

    ai_model = fields.Char(string="Model name", default="gpt-4o-mini", config_parameter="ai_business_assistant.ai_model")
    ai_api_key = fields.Char(string="API Key", config_parameter="ai_business_assistant.ai_api_key")
    ai_base_url = fields.Char(string="Base URL (override)", help="Optional: e.g., https://api.openai.com/v1", config_parameter="ai_business_assistant.ai_base_url")
