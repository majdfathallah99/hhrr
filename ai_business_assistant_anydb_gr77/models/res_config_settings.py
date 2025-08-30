from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ==== Live Voice Chat settings ====
    ai_voice_enabled = fields.Boolean(
        string='Enable Live Voice Chat',
        config_parameter='ai_voice.enabled',
        default=True
    )
    ai_voice_stun_servers = fields.Char(
        string='STUN Servers (comma-separated)',
        help='Example: stun:stun.l.google.com:19302, stun:global.stun.twilio.com:3478',
        config_parameter='ai_voice.stun_servers',
        default='stun:stun.l.google.com:19302'
    )
    ai_voice_turn_servers = fields.Char(
        string='TURN Servers (JSON)',
        help='JSON list of TURN server dicts, e.g. '
             '[{"urls":"turn:turn.example.com:3478","username":"user","credential":"pass"}]',
        config_parameter='ai_voice.turn_servers',
        default='[]'
    )

    # ==== AI Assistant / API settings ====
    ai_api_provider = fields.Selection(
        selection=[('groq', 'Groq'), ('openai', 'OpenAI'), ('custom', 'Custom')],
        string='API Provider',
        default='groq',
        config_parameter='ai_business.api_provider'
    )
    ai_api_base_url = fields.Char(
        string='API Base URL',
        help='Override for the API endpoint base. Keep empty to use provider default.',
        config_parameter='ai_business.api_base_url'
    )
    ai_api_key = fields.Char(
        string='API Key',
        help='Stored in System Parameters (ir.config_parameter).',
        config_parameter='ai_business.api_key'
    )
    ai_api_model = fields.Char(
        string='Default Model',
        help='e.g., llama-3.1-70b-versatile, gpt-4o, etc.',
        config_parameter='ai_business.api_model'
    )
    ai_api_temperature = fields.Float(
        string='Temperature',
        default=0.2,
        config_parameter='ai_business.api_temperature'
    )
    ai_api_max_tokens = fields.Integer(
        string='Max Tokens',
        default=1024,
        config_parameter='ai_business.api_max_tokens'
    )
    ai_api_timeout = fields.Integer(
        string='Request Timeout (sec)',
        default=60,
        config_parameter='ai_business.api_timeout'
    )
