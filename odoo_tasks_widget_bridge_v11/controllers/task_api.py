# -*- coding: utf-8 -*-
from datetime import date
from odoo import http
from odoo.http import request

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
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Cache-Control"] = "no-store"
    return resp

def _get_user_from_token():
    auth = request.httprequest.headers.get("Authorization", "")
    token = None
    if auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1].strip()
    if not token:
        token = request.params.get("token")
    if not token:
        return None
    user = request.env["res.users"].sudo().search([("task_widget_token", "=", token)], limit=1)
    return user if user and user.active else None

def _safe(obj, field, default=None):
    try:
        val = getattr(obj, field)
        return val if val is not None else default
    except Exception:
        return default

class TaskWidgetAPI(http.Controller):

    @http.route("/task_widget/v1/ping", type="http", auth="public", methods=["GET"], csrf=False)
    def ping(self, **kw):
        user = _get_user_from_token()
        if not user:
            return _json_response({"ok": True, "auth": False, "message": "Token required"}, status=401)
        return _json_response({"ok": True, "auth": True, "user_id": user.id, "login": user.login})

    @http.route("/task_widget/v1/tasks", type="http", auth="public", methods=["GET"], csrf=False)
    def tasks(self, **kw):
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
            domain += ["|", ("user_ids", "in", user.id), ("user_id", "=", user.id)]
        if only_open:
            # skip folded stages: safe if stage has fold
            domain.append(("stage_id.fold", "=", False))
        if project_id:
            domain.append(("project_id", "=", project_id))
        if stage_ids:
            domain.append(("stage_id", "in", stage_ids))
        if search:
            domain += ["|", ("name", "ilike", search), ("description", "ilike", search)]

        tasks = Task.search(domain, limit=limit, offset=offset, order=order)
        today = date.today()

        def m2o(record, field):
            try:
                rec = getattr(record, field)
            except Exception:
                rec = None
            return {"id": rec.id, "name": rec.display_name} if rec else None

        payload = []
        for t in tasks:
            dd = _safe(t, "date_deadline", None)
            ks = _safe(t, "kanban_state", "normal") or "normal"
            pr = str(_safe(t, "priority", "0"))
            is_overdue = bool(dd and dd < today)
            payload.append({
                "id": t.id,
                "name": _safe(t, "name", t.display_name),
                "project": m2o(t, "project_id"),
                "stage": m2o(t, "stage_id"),
                "assignee": None,  # could be multiple; use saved API to avoid ambiguity
                "priority": pr,
                "kanban_state": ks if ks in ("normal","blocked","done") else "normal",
                "date_deadline": dd.isoformat() if dd else None,
                "is_overdue": is_overdue,
                "color": _safe(t, "color", 0),
                "tag_ids": [{"id": tag.id, "name": tag.name} for tag in getattr(t, "tag_ids", [])],
                "create_date": _safe(t, "create_date", None).isoformat() if _safe(t, "create_date", None) else None,
                "write_date": _safe(t, "write_date", None).isoformat() if _safe(t, "write_date", None) else None,
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

    @http.route("/task_widget/v1/compact", type="http", auth="public", methods=["GET"], csrf=False)
    def tasks_compact(self, **kw):
        user = _get_user_from_token()
        if not user:
            return _json_response({"error": "Unauthorized: provide a valid token"}, status=401)

        my_only = _truthy(request.params.get("my"), True)
        only_open = _truthy(request.params.get("only_open"), True)
        limit = max(1, min(_int(request.params.get("limit"), 20), 50))

        Task = request.env["project.task"].with_user(user.id)
        domain = [("active", "=", True)]
        if my_only:
            domain += ["|", ("user_ids", "in", user.id), ("user_id", "=", user.id)]
        if only_open:
            domain.append(("stage_id.fold", "=", False))

        tasks = Task.search(domain, limit=limit, order="date_deadline asc")
        today = date.today()
        items = []
        for t in tasks:
            dd = _safe(t, "date_deadline", None)
            ks = _safe(t, "kanban_state", "normal") or "normal"
            items.append({
                "id": t.id,
                "t": _safe(t, "name", t.display_name),
                "d": dd.isoformat() if dd else None,
                "o": bool(dd and dd < today),
                "p": _safe(_safe(t, "project_id", None), "display_name", None),
                "s": _safe(_safe(t, "stage_id", None), "display_name", None),
                "k": ks if ks in ("normal","blocked","done") else "normal",
            })
        return _json_response({"count": len(items), "items": items})

    @http.route("/task_widget/v1/saved", type="http", auth="public", methods=["GET"], csrf=False)
    def api_saved(self, **kw):
        """Return saved items for the token user (stable, tiny)."""
        user = _get_user_from_token()
        if not user:
            return _json_response({"error": "Unauthorized: provide a valid token"}, status=401)
        Items = request.env["task.widget.item"].sudo()
        rows = Items.search([("owner_id", "=", user.id)], order="date_deadline asc, id asc")
        data = [{
            "id": r.task_id.id or r.id,
            "t": r.name,
            "d": r.date_deadline.isoformat() if r.date_deadline else None,
            "o": bool(r.is_overdue),
            "p": r.project_name,
            "s": r.stage_name,
            "k": r.kanban_state or "normal",
        } for r in rows]
        return _json_response({"count": len(data), "items": data})