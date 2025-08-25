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
    kanban_state = fields.Selection([("normal","Normal"),("blocked","Blocked"),("done","Done")], default="normal")
    priority = fields.Selection([("0","0"),("1","1"),("2","2")], default="0")

    _sql_constraints = [
        ("task_owner_unique", "unique(task_id, owner_id)", "Saved item already exists for this user and task."),
    ]

    @api.model
    def _assigned_user_ids(self, task):
        """Return list of user IDs assigned to task, supporting both user_ids and user_id."""
        ids = []
        # m2m in recent versions
        if hasattr(task, "user_ids"):
            ids = list(task.user_ids.ids)
        # fallback m2o
        if not ids and hasattr(task, "user_id"):
            uid = task.user_id.id or False
            ids = [uid] if uid else []
        return ids

    @api.model
    def _vals_from_task(self, t, owner_id):
        dd = getattr(t, "date_deadline", False)
        # normalize priority to string "0|1|2"
        pr = getattr(t, "priority", "0")
        try:
            pr = str(pr)
        except Exception:
            pr = "0"
        # normalize kanban_state to one of selection values
        ks = getattr(t, "kanban_state", False) or "normal"
        if ks not in ("normal", "blocked", "done"):
            ks = "normal"
        return {
            "name": getattr(t, "name", False) or getattr(t, "display_name", False) or "Task",
            "task_id": t.id,
            "owner_id": owner_id,
            "project_name": getattr(getattr(t, "project_id", False), "display_name", False) or False,
            "stage_name": getattr(getattr(t, "stage_id", False), "display_name", False) or False,
            "date_deadline": dd,
            "is_overdue": bool(dd and dd < date.today()),
            "kanban_state": ks,
            "priority": pr,
        }

    @api.model
    def upsert_from_task(self, task):
        """Mirror assignees: create/update for current assignees; remove for others."""
        self = self.sudo()
        assigned = self._assigned_user_ids(task)
        # Remove rows for users who are no longer assigned
        self.search([("task_id", "=", task.id), ("owner_id", "not in", assigned or [0])]).unlink()

        if not getattr(task, "active", True) or not assigned:
            # No assignees or inactive: remove all saved rows
            self.search([("task_id", "=", task.id)]).unlink()
            return False

        # Create/update for each assigned user
        for uid in assigned:
            existing = self.search([("task_id", "=", task.id), ("owner_id", "=", uid)], limit=1)
            vals = self._vals_from_task(task, uid)
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
        return True

    @api.model
    def snapshot_for_user(self, user):
        """Rebuild saved items for the given user from their assigned tasks (active ones)."""
        Task = self.env["project.task"].with_user(user.id)
        domain = [("active", "=", True), "|", ("user_ids", "in", user.id), ("user_id", "=", user.id)]
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