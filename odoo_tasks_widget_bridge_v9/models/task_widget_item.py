# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api

class TaskWidgetItem(models.Model):
    _name = "task.widget.item"
    _description = "Task Widget Saved Item"
    _order = "date_deadline asc, id asc"

    name = fields.Char(required=True, index=True)
    task_id = fields.Many2one("project.task", ondelete="cascade", index=True, required=True)
    owner_id = fields.Many2one("res.users", required=True, index=True)
    project_name = fields.Char()
    stage_name = fields.Char()
    date_deadline = fields.Date()
    is_overdue = fields.Boolean()
    kanban_state = fields.Selection([("normal","Normal"),("blocked","Blocked"),("done","Done")])
    priority = fields.Selection([("0","0"),("1","1"),("2","2")], default="0")

    _sql_constraints = [
        ("task_owner_unique", "unique(task_id, owner_id)", "Saved item already exists for this user and task."),
    ]

    @api.model
    def _vals_from_task(self, t, owner_id):
        dd = t.date_deadline
        return {
            "name": t.name or (t.display_name or "Task"),
            "task_id": t.id,
            "owner_id": owner_id,
            "project_name": t.project_id.display_name if t.project_id else False,
            "stage_name": t.stage_id.display_name if t.stage_id else False,
            "date_deadline": dd,
            "is_overdue": bool(dd and dd < date.today()),
            "kanban_state": t.kanban_state or "normal",
            "priority": t.priority or "0",
        }

    @api.model
    def upsert_from_task(self, task):
        """Ensure a single saved item for the current assignee; remove others."""
        self = self.sudo()
        # Remove for any owners that are not the current assignee
        self.search([("task_id", "=", task.id), ("owner_id", "!=", task.user_id.id or 0)]).unlink()
        if not task.active or not task.user_id:
            # No current assignee or inactive: remove all
            self.search([("task_id", "=", task.id)]).unlink()
            return False
        # Create or update for the current assignee
        existing = self.search([("task_id", "=", task.id), ("owner_id", "=", task.user_id.id)], limit=1)
        vals = self._vals_from_task(task, task.user_id.id)
        if existing:
            existing.write(vals)
            return existing
        else:
            return self.create(vals)

    @api.model
    def snapshot_for_user(self, user):
        """Rebuild saved items for the given user from their assigned tasks (active ones)."""
        Task = self.env["project.task"].with_user(user.id)
        domain = [("active", "=", True), ("user_id", "=", user.id)]
        tasks = Task.search(domain, order="date_deadline asc")
        self.search([("owner_id", "=", user.id)]).unlink()
        for t in tasks:
            self.upsert_from_task(t)
        return True

    @api.model
    def cron_snapshot_all(self):
        Users = self.env["res.users"].sudo()
        token_users = Users.search([("task_widget_token", "!=", False), ("active", "=", True)])
        for u in token_users:
            self.sudo().snapshot_for_user(u)
        return True