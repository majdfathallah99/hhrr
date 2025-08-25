# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class TasksWidgetController(http.Controller):
    def _user_from_token(self, token):
        if not token:
            return None
        return request.env["res.users"].sudo().search([("widget_token", "=", token)], limit=1)

    @http.route("/odoo_widget/ping", type="json", auth="public", methods=["POST"], csrf=False)
    def ping(self, token=None, **kwargs):
        user = self._user_from_token(token)
        if not user:
            return {"ok": False, "error": "bad_token"}
        return {"ok": True}

    @http.route("/odoo_widget/tasks", type="json", auth="public", methods=["POST"], csrf=False)
    def tasks(self, token=None, limit=20, **kwargs):
        user = self._user_from_token(token)
        if not user:
            return {"error": {"code": 401, "message": "Invalid token"}}

        Task = request.env["project.task"].sudo().with_context(lang=user.lang or "en_US")
        dom = ["|", ("user_id", "=", user.id), ("user_ids", "in", [user.id])]
        fields = ["id", "name", "project_id", "stage_id", "date_deadline"]
        tasks = Task.search_read(dom, fields=fields, limit=int(limit), order="date_deadline asc, priority desc, id desc")

        items = []
        for t in tasks:
            project = t["project_id"][1] if isinstance(t.get("project_id"), (list, tuple)) and len(t["project_id"]) > 1 else None
            stage = t["stage_id"][1] if isinstance(t.get("stage_id"), (list, tuple)) and len(t["stage_id"]) > 1 else None
            items.append({
                "id": t["id"],
                "name": t["name"],
                "project": project,
                "stage": stage,
                "deadline": t.get("date_deadline"),
            })

        return {"tasks": items}
