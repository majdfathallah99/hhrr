
from odoo import models, fields, api
class HrDepartment(models.Model):
    _inherit = "hr.department"
    bonus_budget = fields.Float("Annual Bonus Budget")
    bonus_spent = fields.Float(compute="_compute_bonus_totals", store=False)
    bonus_remaining = fields.Float(compute="_compute_bonus_totals", store=False)
    @api.depends("bonus_budget")
    def _compute_bonus_totals(self):
        Bonus = self.env["hr.bonus.request"].sudo()
        for dep in self:
            res = Bonus.read_group(
                domain=[("department_id","=",dep.id),("state","in",["approved","paid"])],
                fields=["amount:sum"], groupby=[]
            )
            spent = res and res[0].get("amount_sum",0.0) or 0.0
            dep.bonus_spent = spent
            dep.bonus_remaining = (dep.bonus_budget or 0.0) - spent
