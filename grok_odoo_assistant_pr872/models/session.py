from odoo import models, fields

class GrokAssistantSession(models.Model):
    _name = "grok.assistant.session"
    _description = "Grok Assistant Session"

    name = fields.Char(default="Session", required=True)
    active = fields.Boolean(default=True)
    last_lang = fields.Selection([("ar","Arabic"),("en","English")], default="en")
    allow_execute = fields.Boolean(string="Allow Tool Execution", default=False)
    message_ids = fields.One2many("grok.assistant.message", "session_id", string="Messages")


class GrokAssistantMessage(models.Model):
    _name = "grok.assistant.message"
    _description = "Grok Assistant Message"
    _order = "id asc"

    session_id = fields.Many2one("grok.assistant.session", required=True, ondelete="cascade")
    role = fields.Selection([("user","User"),("assistant","Assistant"),("system","System")], default="user")
    content = fields.Text()
    detected_lang = fields.Char()
    meta = fields.Text()