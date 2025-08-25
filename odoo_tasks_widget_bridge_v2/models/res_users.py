# -*- coding: utf-8 -*-
import secrets
from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = "res.users"

    task_widget_token = fields.Char(
        string="Task Widget Token",
        copy=False,
        readonly=True,
        help="Personal access token for the Task Widget API. Treat like a password.",
        groups="base.group_system",
        index=True,
    )

    def action_generate_task_widget_token(self):
        for user in self:
            # 32 urlsafe bytes ~ 43 chars
            user.task_widget_token = secrets.token_urlsafe(32)
        return True
