# -*- coding: utf-8 -*-
import json
from datetime import date, datetime
from odoo import http
from odoo.http import request

# Small helper to parse truthy query params
def _truthy(v, default=False):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes", "y", "on")

def _int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default

def _split_ints(s):
    if not s:
        return []
    res = []
    for x in str(s).split(","):
        x = x.strip()
        if not x:
            continue
        try:
            res.append(int(x))
        except Exception:
            pass
    return res

def _json_response(payload, status=200):
    resp = request.make_json_response(payload, status=status)
    # allow calling from Android/web widgets without CORS headaches
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Cache-Control"] = "no-store"
    return resp

def _get_user_from_token():
    # Token can be passed as Authorization: Bearer <token> or as ?token=...
    auth = request.httprequest.headers.get("Authorization", "")
    token = None
    if auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1].strip()
    if not token:
        token = request.params.get("token")
    if not token:
        return None
    # Search user by token with sudo (token is a secret field)
    Users = request.env["res.users"].sudo()
    user = Users.search([("task_widget_token", "=", token)], limit=1)
    return user if user and user.active else None

class TaskWidgetAPI(http.Controller):

    @http.route("/task_widget/v1/ping", type="http", auth="public", methods=["GET"], csrf=False)
    def ping(self, **kw):
        user = _get_user_from_token()
        if not user:
            return _json_response({"ok": True, "auth": False, "message": "Token required"}, status=401)
        return _json_response({"ok": True, "auth": True, "user_id": user.id, "login": user.login})

    @http.route("/task_widget/v1/tasks", type="http", auth="public", methods=["GET"], csrf=False)
    def tasks(self, **kw):
        """Return current user's tasks as JSON.

        Auth:
            - Use Authorization: Bearer <token>
              OR pass ?token=<token> in the query string.

        Query params:
            my: bool (default: 1) -> only tasks assigned to the token user
            only_open: bool (default: 1) -> exclude folded stages
            project_id: int
            stage_ids: comma separated ints
            search: substring to match name/description (ilike)
            limit: int (default: 50, max 200)
            offset: int (default: 0)
            order: one of:
               - date_deadline asc/desc
               - priority asc/desc
               - create_date asc/desc
               - write_date asc/desc
               - sequence asc/desc
        """
        user = _get_user_from_token()
        if not user:
            return _json_response({"error": "Unauthorized: provide a valid token"}, status=401)

        my_only = _truthy(request.params.get("my"), True)
        only_open = _truthy(request.params.get("only_open"), True)
        project_id = _int(request.params.get("project_id"))
        stage_ids = _split_ints(request.params.get("stage_ids"))
        search = (request.params.get("search") or "").strip()

        limit = max(1, min(_int(request.params.get("limit"), 50), 200))
        offset = max(0, _int(request.params.get("offset"), 0) or 0)

        allowed_orders = {
            "date_deadline asc", "date_deadline desc",
            "priority asc", "priority desc",
            "create_date asc", "create_date desc",
            "write_date asc", "write_date desc",
            "sequence asc", "sequence desc",
        }
        order = (request.params.get("order") or "date_deadline asc").lower()
        if order not in allowed_orders:
            order = "date_deadline asc"

        Task = request.env["project.task"].with_user(user.id)
        domain = [("active", "=", True)]
        if my_only:
            domain.append(("user_id", "=", user.id))
        if only_open:
            domain.append(("stage_id.fold", "=", False))
        if project_id:
            domain.append(("project_id", "=", project_id))
        if stage_ids:
            domain.append(("stage_id", "in", stage_ids))
        if search:
            domain += ["|", ("name", "ilike", search), ("description", "ilike", search)]

        tasks = Task.search(domain, limit=limit, offset=offset, order=order)

        # Prefetch related names efficiently
        tasks.read(["name"])  # prefetch
        today = date.today()

        def m2o(record, field):
            rec = record[field]
            return {"id": rec.id, "name": rec.display_name} if rec else None

        payload = []
        for t in tasks:
            dd = t.date_deadline
            is_overdue = False
            if dd:
                try:
                    # date_deadline is a date field
                    is_overdue = dd < today
                except Exception:
                    is_overdue = False

            payload.append({
                "id": t.id,
                "name": t.name,
                "project": m2o(t, "project_id"),
                "stage": m2o(t, "stage_id"),
                "assignee": m2o(t, "user_id"),
                "priority": t.priority,           # string: 0,1,2 per Odoo
                "kanban_state": t.kanban_state,   # normal/blocked/done
                "date_deadline": dd.isoformat() if dd else None,
                "is_overdue": bool(is_overdue),
                "color": t.color,
                "tag_ids": [{"id": tag.id, "name": tag.name} for tag in t.tag_ids],
                "create_date": t.create_date.isoformat() if t.create_date else None,
                "write_date": t.write_date.isoformat() if t.write_date else None,
                "display_name": t.display_name,
            })

        return _json_response({
            "count": len(payload),
            "offset": offset,
            "limit": limit,
            "order": order,
            "my_only": my_only,
            "only_open": only_open,
            "items": payload,
        })

    @http.route("/task_widget/v1/projects", type="http", auth="public", methods=["GET"], csrf=False)
    def projects(self, **kw):
        """List projects visible to the token user (id + name)."""
        user = _get_user_from_token()
        if not user:
            return _json_response({"error": "Unauthorized: provide a valid token"}, status=401)

        Project = request.env["project.project"].with_user(user.id)
        projects = Project.search([("active", "=", True)], order="name asc")
        data = [{"id": p.id, "name": p.display_name} for p in projects]
        return _json_response({"count": len(data), "items": data})

    @http.route("/task_widget/v1/stages", type="http", auth="public", methods=["GET"], csrf=False)
    def stages(self, **kw):
        """List task stages (optionally filtered by project_id)."""
        user = _get_user_from_token()
        if not user:
            return _json_response({"error": "Unauthorized: provide a valid token"}, status=401)

        project_id = request.params.get("project_id")
        domain = [("active", "=", True)]
        if project_id:
            try:
                pid = int(project_id)
                domain.append(("project_ids", "in", [pid]))
            except Exception:
                pass
        Stage = request.env["project.task.type"].with_user(user.id)
        stages = Stage.search(domain, order="sequence asc, name asc")
        data = [{"id": s.id, "name": s.display_name, "fold": s.fold} for s in stages]
        return _json_response({"count": len(data), "items": data})
