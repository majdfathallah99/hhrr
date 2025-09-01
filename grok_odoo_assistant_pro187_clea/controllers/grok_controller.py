from odoo import http
from odoo.http import request

class GrokController(http.Controller):

    @http.route("/grok/ui", type="http", auth="user", website=False)
    def grok_ui(self, **kw):
        session = request.env["grok.assistant.session"].sudo().create({})
        values = {"session_id": session.id, "user_name": request.env.user.display_name}
        return request.render("grok_odoo_assistant_pro17_clean.ui_page", values)

    @http.route("/grok/config", type="http", auth="user", website=False)
    def grok_config(self, **kw):
        values = {"user_name": request.env.user.display_name}
        return request.render("grok_odoo_assistant_pro17_clean.config_page", values)

    @http.route("/grok/chat_http", type="json", auth="user")
    def chat_http(self, message="", session_id=None, approve=False, tool_payload=None):
        # Very simple echo + fake tool gate to keep server-side safe
        reply = ""
        pending_tool = None
        if message:
            if any(ch for ch in message if '؀' <= ch <= 'ۿ'):
                # Arabic detected
                reply = "تفضل — فهمت رسالتك: " + message
            else:
                reply = "Got it — I understood: " + message
            if "create product" in message.lower() or "اضافة منتج" in message:
                pending_tool = '{"tool":"create_product","name":"Demo Product"}'
        if approve and tool_payload:
            reply = "✅ Executed: " + str(tool_payload)
        return {"reply": reply, "pending_tool": pending_tool}