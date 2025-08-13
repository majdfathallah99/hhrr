
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
class HrBonusRequest(models.Model):
    _name = "hr.bonus.request"
    _description = "Bonus Request"
    _inherit = ["mail.thread","mail.activity.mixin"]
    _order = "create_date desc"
    name = fields.Char(default="/", copy=False, tracking=True)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    department_id = fields.Many2one("hr.department", related="employee_id.department_id", store=True, tracking=True)
    type_id = fields.Many2one("hr.bonus.type", required=True, tracking=True)
    amount = fields.Float(tracking=True)
    request_date = fields.Date(default=fields.Date.context_today, tracking=True)
    state = fields.Selection([("draft","Draft"),("to_approve","To Approve"),("approved","Approved"),("refused","Refused"),("paid","Paid")], default="draft", tracking=True, index=True)
    note = fields.Text()
    @api.onchange("type_id","employee_id")
    def _onchange_compute_amount(self):
        for r in self:
            if r.type_id and r.employee_id:
                if r.type_id.amount_type=="fixed":
                    r.amount = r.type_id.amount_fixed or 0.0
                else:
                    wage = r.employee_id.contract_id and r.employee_id.contract_id.wage or 0.0
                    r.amount = (wage or 0.0) * (r.type_id.percent_of_wage or 0.0) / 100.0
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        seq = self.env["ir.sequence"].sudo()
        for rec in recs:
            if not rec.name or rec.name == "/":
                rec.name = seq.next_by_code("hr.bonus.request") or rec.name
        return recs
    def action_submit(self):
        self.write({"state":"to_approve"}); return True
    def action_approve(self):
        for r in self:
            if r.department_id and r.department_id.bonus_remaining < r.amount:
                raise UserError(_("This approval exceeds the department's remaining budget."))
        self.write({"state":"approved"}); return True
    def action_refuse(self):
        self.write({"state":"refused"}); return True
    def action_mark_paid(self):
        self.write({"state":"paid"}); return True
    def action_reset_to_draft(self):
        self.write({"state":"draft"}); return True
    @api.constrains("amount")
    def _check_amount_positive(self):
        for r in self:
            if r.amount <= 0.0:
                raise ValidationError(_("Amount must be greater than zero."))
