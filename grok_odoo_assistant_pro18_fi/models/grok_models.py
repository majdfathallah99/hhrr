from odoo import api, fields, models, _
from odoo.exceptions import UserError

class GrokAssistantSession(models.Model):
    _name = "grok.assistant.session"
    _description = "Grok Assistant Session"
    _order = "id desc"

    name = fields.Char(default="Session", required=True)
    active = fields.Boolean(default=True)
    message_ids = fields.One2many("grok.assistant.message", "session_id", string="Messages")
    last_lang = fields.Selection([("ar", "Arabic"), ("en", "English")], string="Last Language")
    allow_execute = fields.Boolean(string="Allow Execute", default=False)

class GrokAssistantMessage(models.Model):
    _name = "grok.assistant.message"
    _description = "Grok Assistant Message"
    _order = "id asc"

    session_id = fields.Many2one("grok.assistant.session", required=True, ondelete="cascade")
    role = fields.Selection([("system","System"),("user","User"),("assistant","Assistant")], default="user", required=True)
    content = fields.Text(required=True)
    detected_lang = fields.Selection([("ar", "Arabic"), ("en", "English")], string="Detected Language")
    meta = fields.Json(string="Metadata")

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    grok_provider = fields.Selection([
        ("xai", "xAI (Grok)"),
        ("groq", "Groq"),
        ("openai", "OpenAI"),
        ("custom", "Custom (OpenAI-compatible)")
    ], default="xai", string="LLM Provider")

    grok_endpoint = fields.Char(string="API Base URL (optional)",
                                help="For custom/OpenAI-compatible backends, e.g., https://api.my-llm.example")
    grok_model = fields.Char(string="Model", default="grok-2-latest")
    grok_api_key = fields.Char(string="API Key")
    grok_temperature = fields.Float(default=0.2)
    grok_allowed_models = fields.Char(
        string="Allowed Odoo Models (comma-separated)",
        default="product.product,product.template,sale.order,sale.order.line,purchase.order,purchase.order.line,res.partner"
    )

    def set_values(self):
        super().set_values()
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("grok.provider", self.grok_provider or "")
        params.set_param("grok.endpoint", self.grok_endpoint or "")
        params.set_param("grok.model", self.grok_model or "")
        params.set_param("grok.api_key", self.grok_api_key or "")
        params.set_param("grok.temperature", self.grok_temperature or 0.0)
        params.set_param("grok.allowed_models", self.grok_allowed_models or "")

    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()
        res.update(
            grok_provider=params.get_param("grok.provider") or "xai",
            grok_endpoint=params.get_param("grok.endpoint") or "",
            grok_model=params.get_param("grok.model") or "grok-2-latest",
            grok_api_key=params.get_param("grok.api_key") or "",
            grok_temperature=float(params.get_param("grok.temperature") or 0.2),
            grok_allowed_models=params.get_param("grok.allowed_models") or "",
        )
        return res
