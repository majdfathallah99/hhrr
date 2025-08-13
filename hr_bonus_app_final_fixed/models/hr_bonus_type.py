
from odoo import models, fields

class HrBonusType(models.Model):
    _name = "hr.bonus.type"
    _description = "Bonus Type"
    _order = "name"
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    amount_type = fields.Selection([("fixed","Fixed amount"),("percent","Percentage of wage")], required=True, default="fixed")
    amount_fixed = fields.Float(default=0.0)
    percent_of_wage = fields.Float()
    active = fields.Boolean(default=True)
