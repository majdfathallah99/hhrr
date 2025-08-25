# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api

class TaskWidgetItem(models.Model):
    _name = "task.widget.item"
    _description = "Task Widget Saved Item"
    _order = "date_deadline asc, id asc"

    name = fields.Char(required=True, index=True)
    task_id = fields.Many2one("project.task", ondelete="cascade", index=True)
    owner_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    project_name = fields.Char()
    stage_name = fields.Char()
    date_deadline = fields.Date()
    is_overdue = fields.Boolean()
    kanban_state = fields.Selection([("normal","Normal"),("blocked","Blocked"),("done","Done")])
    priority = fields.Selection([("0","0"),("1","1"),("2","2")], default="0")

    @api.model
    def snapshot_for_user(self, user):
        Task = self.env["project.task"].with_user(user.id)
        domain = [("active", "=", True), ("user_id", "=", user.id)]
        tasks = Task.search(domain, order="date_deadline asc")
        self.search([("owner_id", "=", user.id)]).unlink()
        today = date.today()
        vals_list = []
        for t in tasks:
            dd = t.date_deadline
            vals_list.append({
                "name": t.name or (t.display_name or "Task"),
                "task_id": t.id,
                "owner_id": user.id,
                "project_name": t.project_id.display_name if t.project_id else False,
                "stage_name": t.stage_id.display_name if t.stage_id else False,
                "date_deadline": dd,
                "is_overdue": bool(dd and dd < today),
                "kanban_state": t.kanban_state or "normal",
                "priority": t.priority or "0",
            })
        if vals_list:
            self.create(vals_list)
        return len(vals_list)

    @api.model
    def cron_snapshot_all(self):
        Users = self.env["res.users"].sudo()
        token_users = Users.search([("task_widget_token", "!=", False), ("active", "=", True)])
        for u in token_users:
            self.sudo().snapshot_for_user(u)
        return True