from odoo import http
from odoo.http import request

class GrokController(http.Controller):

    @http.route("/grok/ui", type="http", auth="user", methods=["GET","POST"], csrf=False, website=False)
    def grok_ui(self, **kw):
        # Create a fresh session (simple placeholder)
        session = request.env["grok.assistant.session"].sudo().create({})
        user_message = (kw.get("message") or "").strip()
        reply = ""
        if user_message:
            # minimal bilingual echo — no JS/JSON used
            if any(ord(ch) >= 0x0600 and ord(ch) <= 0x06FF for ch in user_message):
                reply = "تفضل — فهمت رسالتك: " + user_message
            else:
                reply = "Got it — I understood: " + user_message
            # store messages
            request.env["grok.assistant.message"].sudo().create({
                "session_id": session.id, "role":"user", "content": user_message
            })
            request.env["grok.assistant.message"].sudo().create({
                "session_id": session.id, "role":"assistant", "content": reply
            })
        values = {
            "session_id": session.id,
            "user_name": request.env.user.display_name,
            "user_message": user_message,
            "reply": reply,
        }
        return request.render("grok_odoo_assistant_pro17_clean.ui_page", values)

    @http.route("/grok/config", type="http", auth="user", website=False)
    def grok_config(self, **kw):
        values = {"user_name": request.env.user.display_name}
        return request.render("grok_odoo_assistant_pro17_clean.config_page", values)