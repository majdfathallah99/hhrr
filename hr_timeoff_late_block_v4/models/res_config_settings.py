from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    restrict_late_timeoff_submission = fields.Boolean(
        related='company_id.restrict_late_timeoff_submission',
        readonly=False,
        string='Block late Time Off submissions (> 2 days)',
        help='When enabled, employees cannot submit a Time Off request more than 2 days after the leave start date.'
    )