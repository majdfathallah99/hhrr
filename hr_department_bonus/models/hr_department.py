
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrDepartment(models.Model):
    _inherit = "hr.department"

    bonus_budget = fields.Monetary(string="Bonus Budget", help="Optional budget for bonuses.",
                                   currency_field="company_currency_id")
    bonus_spent = fields.Monetary(string="Bonus Spent", compute="_compute_bonus_totals",
                                  currency_field="company_currency_id", store=False)
    bonus_remaining = fields.Monetary(string="Bonus Remaining", compute="_compute_bonus_totals",
                                      currency_field="company_currency_id", store=False)
    company_currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True)

    bonus_request_count = fields.Integer(compute="_compute_bonus_request_count")

    def _compute_bonus_request_count(self):
        for dep in self:
            dep.bonus_request_count = self.env["hr.bonus.request"].sudo().search_count([
                ("department_id", "=", dep.id),
                ("state", "in", ["to_approve", "approved", "paid"]),
            ])

    @api.depends("bonus_budget")
    def _compute_bonus_totals(self):
        Bonus = self.env["hr.bonus.request"].sudo()
        for dep in self:
            approved = Bonus.read_group(
                domain=[("department_id", "=", dep.id), ("state", "in", ["approved", "paid"])],
                fields=["amount:sum"],
                groupby=[]
            )
            spent = approved and approved[0].get("amount_sum") or 0.0
            dep.bonus_spent = spent
            dep.bonus_remaining = (dep.bonus_budget or 0.0) - spent
