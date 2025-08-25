# -*- coding: utf-8 -*-
import secrets
from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    widget_token = fields.Char("Widget Token", copy=False, groups="base.group_user")

    def action_generate_widget_token(self):
        for user in self:
            user.widget_token = secrets.token_urlsafe(32)
        return True
