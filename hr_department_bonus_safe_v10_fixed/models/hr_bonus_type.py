
# -*- coding: utf-8 -*-
from odoo import models, fields

class HrBonusType(models.Model):
    _name = "hr.bonus.type"
    _description = "Bonus Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Short code for reporting (e.g. BONUS).")
    amount_type = fields.Selection([("fixed", "Fixed amount"), ("percent", "Percentage of wage")],
                                   default="fixed", required=True)
    amount_fixed = fields.Float("Fixed Amount", default=0.0)
    percent_of_wage = fields.Float("Percent of Wage", help="If set, amount = wage * percent / 100")
    active = fields.Boolean(default=True)
