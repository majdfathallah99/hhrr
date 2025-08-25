from odoo import fields, models
import secrets

class ResUsers(models.Model):
    _inherit = "res.users"

    widget_token = fields.Char("Widget Token", copy=False, readonly=True)

    def action_generate_widget_token(self):
        for user in self:
            user.widget_token = secrets.token_hex(16)
