
from odoo import models, fields, api

class HrDepartment(models.Model):
    _inherit = "hr.department"

    bonus_budget = fields.Float("Annual Bonus Budget")
    bonus_spent = fields.Float(compute="_compute_bonus_totals")
    bonus_remaining = fields.Float(compute="_compute_bonus_totals")

    @api.depends('bonus_budget')
    def _compute_bonus_totals(self):
        Bonus = self.env['hr.bonus.request'].sudo()
        for dep in self:
            data = Bonus.read_group(
                domain=[('department_id','=',dep.id),('state','in',['approved','paid'])],
                fields=['amount:sum'],
                groupby=[]
            )
            spent = data and data[0].get('amount_sum') or 0.0
            dep.bonus_spent = spent or 0.0
            dep.bonus_remaining = (dep.bonus_budget or 0.0) - (spent or 0.0)
