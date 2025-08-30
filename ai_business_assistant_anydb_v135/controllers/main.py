
from odoo import http
from odoo.http import request
import json

class AIAssistantController(http.Controller):
    @http.route("/ai_assistant", type="http", auth="user", website=True)
    def ai_assistant_page(self, **kw):
        # Minimal chat page uses website template below
        return request.render("ai_business_assistant_anydb_v128_voice_FIXED.ai_chat_page", {})

    @http.route("/ai_assistant/query_http", type="json", auth="user", csrf=False, methods=["POST"])
    def ai_query_http(self, message=None, **kw):
        # Basic echo to avoid server errors; replace with real LLM/tool logic later.
        if not message or not message.strip():
            return {"text": "Please say or type something.", "tool_calls": [], "tool_results": []}
        reply = f"You said: {message.strip()}"
        return {"text": reply, "tool_calls": [], "tool_results": []}

    @http.route("/ai_assistant/voice", type="http", auth="user", website=True)
    def ai_voice_page(self, **kw):
        return request.render("ai_business_assistant_anydb_v128_voice_FIXED.ai_voice_page", {})
