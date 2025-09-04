from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_api_key = fields.Char(string="API Key", config_parameter="ai_assistant.api_key")
    ai_model = fields.Char(string="Model", default="gpt-4o-mini", config_parameter="ai_assistant.model")
    ai_base_url = fields.Char(string="Base URL", config_parameter="ai_assistant.base_url")
    ai_system_prompt = fields.Text(string="System Prompt", config_parameter="ai_assistant.system_prompt")
