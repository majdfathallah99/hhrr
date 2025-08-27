from odoo import models, fields, _

class ResCompany(models.Model):
    _inherit = "res.company"

    restrict_late_timeoff_submission = fields.Boolean(
        string="Block late Time Off submissions (> 2 days)",
        help="When enabled, employees cannot submit a Time Off request more than 2 days after the leave start date.",
    )