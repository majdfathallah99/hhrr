
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class HrBonusRequest(models.Model):
    _name = "hr.bonus.request"
    _description = "Employee Bonus Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Reference", default=lambda self: _("New"), copy=False, readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, tracking=True)
    department_id = fields.Many2one("hr.department", string="Department", required=True, tracking=True)
    company_id = fields.Many2one("res.company", related="employee_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True, store=True)

    bonus_type_id = fields.Many2one("hr.bonus.type", string="Bonus Type", required=True, tracking=True)
    amount = fields.Monetary(required=True, tracking=True)
    description = fields.Text()

    request_date = fields.Date(default=fields.Date.context_today, tracking=True)
    state = fields.Selection([
        ("draft", "To Submit"),
        ("to_approve", "To Approve"),
        ("approved", "Approved"),
        ("paid", "Paid"),
        ("refused", "Refused"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    manager_id = fields.Many2one("res.users", string="Manager", tracking=True,
                                 help="Manager who approved.")
    hr_user_id = fields.Many2one("res.users", string="HR Approver", tracking=True)

    # Computed helper flags for view logic
    can_approve = fields.Boolean(compute="_compute_can_approve")
    can_pay = fields.Boolean(compute="_compute_can_pay")

    @api.depends_context("uid")
    def _compute_can_approve(self):
        is_hr = self.env.user.has_group("hr.group_hr_user")
        for rec in self:
            mgr = rec.employee_id.parent_id and rec.employee_id.parent_id.user_id
            rec.can_approve = bool(is_hr or (mgr and mgr.id == self.env.uid))

    def _compute_can_pay(self):
        for rec in self:
            rec.can_pay = self.env.user.has_group("hr.group_hr_user") and rec.state == "approved"

    @api.onchange("employee_id")
    def _onchange_employee_id_set_department(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.bonus.request") or _("New")
            if not vals.get("department_id") and vals.get("employee_id"):
                emp = self.env["hr.employee"].browse(vals["employee_id"])
                vals["department_id"] = emp.department_id.id
        recs = super().create(vals_list)
        # Schedule activity for the manager
        for rec in recs:
            manager_user = rec.employee_id.parent_id.user_id
            if manager_user:
                rec.activity_schedule("mail.mail_activity_data_todo", user_id=manager_user.id,
                                      summary=_("Bonus request to approve"),
                                      note=_("Please review the bonus request."))
        return recs

    # Transitions
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                continue
            rec.write({"state": "to_approve"})
            manager_user = rec.employee_id.parent_id.user_id
            if manager_user:
                rec.activity_schedule("mail.mail_activity_data_todo", user_id=manager_user.id,
                                      summary=_("Approve Bonus Request"),
                                      note=_("Please approve or refuse the request %s") % rec.name)

    def action_manager_approve(self):
        for rec in self:
            if rec.state != "to_approve":
                raise UserError(_("Only requests in 'To Approve' can be manager-approved."))
            rec.write({"state": "approved", "manager_id": self.env.user.id})

    def action_refuse(self, reason=False):
        for rec in self:
            rec.write({"state": "refused"})
            rec.message_post(body=_("Refused. %s") % (reason or ""))

    def action_cancel(self):
        for rec in self:
            if rec.state in ("paid",):
                raise UserError(_("Cannot cancel a paid request."))
            rec.write({"state": "cancelled"})

    def action_mark_paid(self):
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("Only approved requests can be paid."))
            rec._check_budget()
            rec.write({"state": "paid"})
            # Payroll integration (optional, auto-detected)
            rec._create_payslip_input()

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state not in ("refused", "cancelled"):
                raise UserError(_("Only refused or cancelled requests can be reset to draft."))
            rec.write({"state": "draft"})

    # Budget check
    def _check_budget(self):
        for rec in self:
            dep = rec.department_id
            if dep.bonus_budget and rec.amount:
                remaining = dep.bonus_remaining
                if remaining < rec.amount - 1e-6:
                    raise ValidationError(_("Insufficient department bonus budget. Remaining: %s") % remaining)

    # Payroll integration (safe & optional)
    def _create_payslip_input(self):
        """Attach this paid bonus as an input line to the employee's draft payslip
        covering the request_date if hr_payroll is present. Otherwise just notify HR.
        """
        # Make sure Payroll models exist
        if not self.env['ir.model']._get('hr.payslip') or not self.env['ir.model']._get('hr.payslip.input'):
            return
        for rec in self:
            if not rec.request_date:
                continue
            Payslip = self.env['hr.payslip'].sudo()
            # Find a draft/verify payslip covering the request date
            slip = Payslip.search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ('draft', 'verify')),
                ('date_from', '<=', rec.request_date),
                ('date_to', '>=', rec.request_date),
            ], limit=1)
            if not slip:
                rec.message_post(body=_("Payroll: No draft payslip found for %s on %s. "
                                        "Add input (Code: %s, Amount: %s) when generating payslip.")
                                        % (rec.employee_id.name, rec.request_date, rec.bonus_type_id.code or 'BONUS', rec.amount))
                continue

            Input = self.env['hr.payslip.input'].sudo()

            # Odoo 17+: hr.payslip.input requires an input_type_id (Many2one to hr.payslip.input.type)
            InputTypeModel = self.env["ir.model"]._get("hr.payslip.input.type")
            input_type = False
            code_val = rec.bonus_type_id.code or "BONUS"
            if InputTypeModel:
                InputType = self.env["hr.payslip.input.type"].sudo()
                input_type = InputType.search([("code", "=", code_val)], limit=1)
                if not input_type:
                    input_type = InputType.create({
                        "name": rec.bonus_type_id.name or "Bonus",
                        "code": code_val,
                    })

            # Determine payslip foreign key field
            slip_field = 'payslip_id' if 'payslip_id' in Input._fields else ('slip_id' if 'slip_id' in Input._fields else None)
            vals = {
                'name': rec.bonus_type_id.name or 'Bonus',
                # 'code' field may not exist in v17 inputs; set it only if available below
                'amount': rec.amount,
            }
            # set input_type_id (required in v17)
            if 'input_type_id' in Input._fields and input_type:
                vals['input_type_id'] = input_type.id
            # keep compatibility with editions having 'code' on input
            if 'code' in Input._fields:
                vals['code'] = code_val
            # Link to contract if supported
            if 'contract_id' in Input._fields:
                Contract = self.env['hr.contract'].sudo()
                contract = Contract.search([('employee_id', '=', rec.employee_id.id), ('state', 'in', ('open', 'trial'))], limit=1)
                if contract:
                    vals['contract_id'] = contract.id
            if slip_field:
                vals[slip_field] = slip.id
            Input.create(vals)
            rec.message_post(body=_("Payroll input created on payslip %s (Code: %s, Amount: %s).")
                                    % (slip.number or slip.name or slip.id, vals.get('code'), vals.get('amount')))

    def name_get(self):
        return [(r.id, "%s - %s" % (r.name, r.employee_id.name or "")) for r in self]
