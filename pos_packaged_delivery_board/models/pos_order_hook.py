# -*- coding: utf-8 -*-
from odoo import models

class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_pos_order_paid(self):
        # Call original validation first
        res = super().action_pos_order_paid()
        # Immediately create board cards for changed-UoM lines
        self.sudo().env["pos.packaged.card"].create_from_one_order(self)
        return res
