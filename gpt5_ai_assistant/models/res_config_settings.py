
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_api_key = fields.Char(string="API Key", config_parameter="ai_assistant.api_key")
    ai_model = fields.Char(string="Model", default="gpt-4o-mini", config_parameter="ai_assistant.model",
                           help="Any OpenAI-compatible chat model, e.g., 'gpt-4o-mini', 'gpt-3.5-turbo', or a local model name.")
    ai_base_url = fields.Char(string="Base URL (optional)",
                              config_parameter="ai_assistant.base_url",
                              help="Optional base URL for OpenAI-compatible servers (e.g., http://127.0.0.1:1234/v1). Leave empty for OpenAI default.")
    ai_system_prompt = fields.Text(string="System Prompt",
                                   config_parameter="ai_assistant.system_prompt",
                                   default="You are a helpful AI assistant inside Odoo. Answer succinctly and can reference Odoo data when asked.")
