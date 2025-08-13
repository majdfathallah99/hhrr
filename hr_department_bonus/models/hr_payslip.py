
# -*- coding: utf-8 -*-
from odoo import models, api, _

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _sync_bonus_inputs(self):
        """Collect all PAID bonus requests for this payslip period and create/update payslip inputs.
        Groups by Bonus Type code (e.g., BONUS, PERF). Requires hr.payslip.input.type per code.
        """
        # Models may not exist if payroll not installed; guard anyway.
        if not self.env['ir.model']._get('hr.bonus.request') or not self.env['ir.model']._get('hr.payslip.input.type'):
            return

        Bonus = self.env['hr.bonus.request'].sudo()
        Input = self.env['hr.payslip.input'].sudo()
        InputType = self.env['hr.payslip.input.type'].sudo()

        for slip in self:
            # gather totals per bonus code within slip period, PAID state only
            domain = [
                ('employee_id', '=', slip.employee_id.id),
                ('state', '=', 'paid'),
                ('request_date', '>=', slip.date_from),
                ('request_date', '<=', slip.date_to),
            ]
            bonuses = Bonus.search(domain)
            totals = {}
            for b in bonuses:
                code = (b.bonus_type_id.code or 'BONUS').upper()
                totals[code] = totals.get(code, 0.0) + b.amount

            if not totals:
                continue

            # Ensure input types exist for each code
            code2type = {}
            for code in totals.keys():
                itype = InputType.search([('code', '=', code)], limit=1)
                if not itype:
                    itype = InputType.create({'name': code, 'code': code})
                code2type[code] = itype

            # Remove prior auto-generated inputs for these codes to avoid duplicates (idempotent)
            existing = Input.search([
                ('payslip_id', '=', slip.id),
                ('input_type_id.code', 'in', list(totals.keys())),
            ])
            existing.unlink()

            # Create fresh inputs per code total
            for code, amount in totals.items():
                vals = {
                    'payslip_id': slip.id,
                    'input_type_id': code2type[code].id,
                    'amount': amount,
                    'name': _('Bonus (%s)') % code,
                }
                # add contract if field exists
                if 'contract_id' in Input._fields and slip.contract_id:
                    vals['contract_id'] = slip.contract_id.id
                # for editions that still have 'code' field
                if 'code' in Input._fields:
                    vals['code'] = code
                Input.create(vals)

    def compute_sheet(self):
        # Before computing, sync bonus inputs
        self._sync_bonus_inputs()
        return super().compute_sheet()
