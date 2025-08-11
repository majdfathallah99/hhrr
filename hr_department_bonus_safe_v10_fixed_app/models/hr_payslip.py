
# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def action_sync_bonus_inputs(self):
        """Manual action: push approved bonus amounts into payslip inputs.
        Safe-guarded: if payroll input models are missing, do nothing.
        """
        self.ensure_one()
        # Check models exist (varies between versions)
        Input = self.env.get("hr.payslip.input")
        InputType = self.env.get("hr.payslip.input.type") or self.env.get("hr.rule.input")

        if not (Input and InputType):
            # Payroll not fully available; do nothing safely
            return True

        slip = self
        employee = slip.employee_id
        if not employee:
            raise UserError(_("No employee on this payslip."))

        # Sum approved/pending-paid bonuses for this employee in the month of the slip
        domain = [("employee_id", "=", employee.id), ("state", "in", ["approved", "paid"])]
        # Optional date filtering if available on the model
        if "request_date" in self.env["hr.bonus.request"]._fields and slip.date_from and slip.date_to:
            domain += [("request_date", ">=", slip.date_from), ("request_date", "<=", slip.date_to)]

        bonuses = self.env["hr.bonus.request"].search(domain)
        totals = {}
        for b in bonuses:
            code = b.type_id.code or "BONUS"
            totals[code] = totals.get(code, 0.0) + (b.amount or 0.0)

        # Map codes to input types (create if missing on hr.payslip.input.type)
        code2type = {}
        for code in totals.keys():
            it = InputType.search([("code", "=", code)], limit=1) if "code" in InputType._fields else InputType.search([("name","=",code)], limit=1)
            if not it:
                vals = {"name": code}
                if "code" in InputType._fields:
                    vals["code"] = code
                it = InputType.create(vals)
            code2type[code] = it

        # Remove existing inputs for these codes on this slip, then recreate
        if "input_type_id" in Input._fields and "payslip_id" in Input._fields:
            existing = Input.search([("payslip_id", "=", slip.id)])
            # Narrow by code if possible
            if "code" in Input._fields:
                existing = existing.filtered(lambda r: r.code in totals.keys())
            existing.unlink()

            for code, amount in totals.items():
                vals = {"payslip_id": slip.id, "amount": amount, "name": _("Bonus (%s)") % code}
                if "input_type_id" in Input._fields:
                    vals["input_type_id"] = code2type[code].id
                if "contract_id" in Input._fields and slip.contract_id:
                    vals["contract_id"] = slip.contract_id.id
                if "code" in Input._fields:
                    vals["code"] = code
                Input.create(vals)

        return True
