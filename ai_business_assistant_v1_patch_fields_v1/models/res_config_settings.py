from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Fields referenced by ai_assistant_views.xml in V1
    ai_enabled = fields.Boolean(
        string='Enable AI Assistant',
        config_parameter='ai_business_v1.ai_enabled',
        default=True,
    )
    ai_superuser_mode = fields.Boolean(
        string='Superuser Mode (Bypass ACL in AI calls)',
        help='If enabled, backend AI calls may run as superuser. Use with care.',
        config_parameter='ai_business_v1.ai_superuser_mode',
        default=False,
    )
    ai_provider = fields.Selection(
        selection=[('groq', 'Groq'), ('openai', 'OpenAI'), ('custom', 'Custom')],
        string='AI Provider',
        config_parameter='ai_business_v1.ai_provider',
        default='groq',
    )
    ai_model = fields.Char(
        string='Default Model',
        help='e.g., llama-3.1-70b-versatile, gpt-4o, etc.',
        config_parameter='ai_business_v1.ai_model',
    )

    # Extras
    ai_base_url = fields.Char(
        string='API Base URL',
        config_parameter='ai_business_v1.ai_base_url',
    )
    ai_api_key = fields.Char(
        string='API Key',
        config_parameter='ai_business_v1.ai_api_key',
    )
    ai_temperature = fields.Float(
        string='Temperature',
        config_parameter='ai_business_v1.ai_temperature',
        default=0.2,
    )
    ai_max_tokens = fields.Integer(
        string='Max Tokens',
        config_parameter='ai_business_v1.ai_max_tokens',
        default=1024,
    )
    ai_timeout = fields.Integer(
        string='Request Timeout (sec)',
        config_parameter='ai_business_v1.ai_timeout',
        default=60,
    )
