
# -*- coding: utf-8 -*-
from odoo import models, fields

class HrBonusType(models.Model):
    _name = "hr.bonus.type"
    _description = "Bonus Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Short code used for payroll integration (e.g., 'BONUS').")
    amount_type = fields.Selection([("fixed", "Fixed amount"), ("percent", "Percentage of wage")],
                                   default="fixed", required=True)
    default_amount = fields.Monetary(string="Default Amount")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id, required=True)
    active = fields.Boolean(default=True)
