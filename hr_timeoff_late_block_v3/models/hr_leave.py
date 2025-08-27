from odoo import models, fields, _
from odoo.exceptions import ValidationError

class HrLeave(models.Model):
    _inherit = "hr.leave"

    def action_confirm(self):
        self._check_late_submission_policy()
        return super().action_confirm()

    def _check_late_submission_policy(self):
        company = (self.company_id or self.employee_id.company_id or self.env.company)
        if not company.restrict_late_timeoff_submission:
            return
        today = fields.Date.context_today(self)
        for leave in self:
            # Use the first day of the leave as the "actual date"
            start_date = leave.request_date_from or (leave.date_from and leave.date_from.date())
            if not start_date:
                # If we cannot compute a start date (edge case), skip the check
                continue
            if today > start_date:
                delta_days = (today - start_date).days
                if delta_days > 2:
                    raise ValidationError(
                        _(
                            "Sorry, you cannot submit a Time Off request more than 2 days after the actual date.\n"
                            "Start date: %s — Today: %s (difference: %s days)."
                        )
                        % (start_date, today, delta_days)
                    )