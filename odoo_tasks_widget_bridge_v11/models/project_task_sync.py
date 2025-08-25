# -*- coding: utf-8 -*-
from odoo import models, api

class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        items = self.env["task.widget.item"].sudo()
        for t in records:
            try:
                items.upsert_from_task(t)
            except Exception:
                # Never block task creation due to snapshot issues
                pass
        return records

    def write(self, vals):
        res = super().write(vals)
        items = self.env["task.widget.item"].sudo()
        for t in self:
            try:
                items.upsert_from_task(t)
            except Exception:
                # Don't block writes
                pass
        return res

    def unlink(self):
        items = self.env["task.widget.item"].sudo()
        for t in self:
            try:
                items.search([("task_id", "=", t.id)]).unlink()
            except Exception:
                pass
        return super().unlink()