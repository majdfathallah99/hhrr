from odoo import http
from odoo.http import request

class GrokController(http.Controller):

    @http.route("/grok/ui", type="http", auth="user", website=False)
    def grok_ui(self, **kw):
        session = request.env["grok.assistant.session"].sudo().create({})
        values = {"session_id": session.id, "user_name": request.env.user.display_name}
        try:
            return request.render("grok_odoo_assistant_pro17_clean.ui_page", values)
        except Exception:
            html = ("<html><head><meta charset='utf-8'><title>Grok Assistant (fallback)</title></head>"
                    "<body style='font-family:system-ui;max-width:920px;margin:2rem auto'>"
                    "<h2>Grok Assistant (fallback)</h2>"
                    "<div id='chat' style='border:1px solid #ddd;border-radius:10px;padding:1rem;min-height:240px'></div>"
                    "<div style='display:flex;gap:.5rem;margin-top:1rem'>"
                    "<input id='msg' placeholder='اكتب هنا / Type here...' style='flex:1;padding:.6rem;border:1px solid #ccc;border-radius:8px'/>"
                    "<button id='sendBtn'>Send</button></div>"
                    "<script>(function(){var sid={sid};var chat=document.getElementById('chat');var msg=document.getElementById('msg');"
                    "var sendBtn=document.getElementById('sendBtn');function a(r,t){var d=document.createElement('div');d.innerHTML='<b>'+r+':</b> '+t;chat.appendChild(d);}"
                    "async function rpc(u,p){var r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',params:p,id:Date.now()})});"
                    "var j=await r.json();return j.result||j;}"
                    "sendBtn.onclick=async function(){var t=(msg.value||'').trim();if(!t)return;a('You',t);msg.value='';var res=await rpc('/grok/chat_http',{message:t,session_id:sid});"
                    "a('Assistant',res.reply||'');};})();</script></body></html>").format(sid=values.get("session_id") or 0)
            return request.make_response(html, headers=[("Content-Type","text/html; charset=utf-8")])

    @http.route("/grok/config", type="http", auth="user", website=False)
    def grok_config(self, **kw):
        values = {"user_name": request.env.user.display_name}
        try:
            return request.render("grok_odoo_assistant_pro17_clean.config_page", values)
        except Exception:
            html = "<html><body style='font-family:system-ui;max-width:920px;margin:2rem auto'><h2>Settings (fallback)</h2></body></html>"
            return request.make_response(html, headers=[("Content-Type","text/html; charset=utf-8")])

    @http.route("/grok/chat_http", type="json", auth="user")
    def chat_http(self, message="", session_id=None, approve=False, tool_payload=None):
        reply = ""
        pending_tool = None
        if message:
            # Simple Arabic detection range
            if any(ord(ch) >= 0x0600 and ord(ch) <= 0x06FF for ch in message):
                reply = "تفضل — فهمت رسالتك: " + message
            else:
                reply = "Got it — I understood: " + message
            if "create product" in message.lower() or "اضافة منتج" in message:
                pending_tool = '{"tool":"create_product","name":"Demo Product"}'
        if approve and tool_payload:
            reply = "✅ Executed: " + str(tool_payload)
        return {"reply": reply, "pending_tool": pending_tool}
