
from odoo import models, fields

class HrBonusType(models.Model):
    _name = "hr.bonus.type"
    _description = "Bonus Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    amount_type = fields.Selection([('fixed','Fixed'),('percent','Percent of wage')], default='fixed', required=True)
    amount_fixed = fields.Float("Fixed Amount", default=0.0)
    percent_of_wage = fields.Float("Percent of Wage")
    active = fields.Boolean(default=True)
