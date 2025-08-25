from odoo import http
from odoo.http import request

class TasksWidgetController(http.Controller):

    @http.route('/tasks_widget/api/v1/ping', type='json', auth="none", csrf=False)
    def ping(self):
        return {"ok": True, "pong": True}

    @http.route('/tasks_widget/api/v1/tasks', type='json', auth="none", csrf=False)
    def tasks(self, token=None, limit=20):
        if not token:
            return {"error": "missing token"}

        user = request.env['res.users'].sudo().search([('widget_token', '=', token)], limit=1)
        if not user:
            return {"error": "invalid token"}

        domain = ['|', ('user_id', '=', user.id), ('user_ids', 'in', [user.id])]
        tasks = request.env['project.task'].sudo().search(domain, limit=limit, order="date_deadline asc, priority desc, id desc")

        result = []
        for t in tasks:
            result.append({
                "id": t.id,
                "name": t.name or "",
                "project": t.project_id.name or "",
                "stage": t.stage_id.name or "",
                "deadline": (t.date_deadline or "") if hasattr(t, 'date_deadline') else ""
            })
        return {"ok": True, "tasks": result}
