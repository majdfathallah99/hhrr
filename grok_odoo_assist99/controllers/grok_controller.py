from odoo import http
from odoo.http import request

class GrokController(http.Controller):

    @http.route("/grok/ui", type="http", auth="user", website=False)
    def grok_ui(self, **kw):
        session =  request.env["grok.assistant.session"].sudo().create({})
        values = {"session_id": session.id, "user_name": request.env.user.display_name}
        try:
            return request.render("grok_odoo_assistant_pro17_clean.ui_page", values)
        except Exception as e:
            html = f"""<html><head><meta charset='utf-8'><title>Grok Assistant (fallback)</title></head>
            <body style='font-family:system-ui;max-width:920px;margin:2rem auto'>
            <h2>Grok Assistant (fallback)</h2>
            <div id='err' style='color:#b00;opacity:.8;font-size:.9rem;margin-bottom:8px'>Template render failed: {e}</div>
            <div id="chat" style="border:1px solid #ddd;border-radius:10px;padding:1rem;min-height:240px"></div>
            <div style="display:flex;gap:.5rem;margin-top:1rem">
                <input id="msg" placeholder="اكتب هنا / Type here..." style="flex:1;padding:.6rem;border:1px solid #ccc;border-radius:8px"/>
                <button id="sendBtn">Send</button>
            </div>
            <script>
            (function(){
                const sid = %(sid)s;
                const chat = document.getElementById('chat');
                const msg = document.getElementById('msg');
                const sendBtn = document.getElementById('sendBtn');
                function append(r,t){var d=document.createElement('div');d.innerHTML='<b>'+r+':</b> '+t;chat.appendChild(d);}
                async function rpc(route, params){
                    const r = await fetch(route,{method:'POST',headers:{'Content-Type':'application/json'},
                        body: JSON.stringify({"jsonrpc":"2.0","method":"call","params":params,"id":Date.now()})});
                    const j = await r.json(); return j.result || j;
                }
                sendBtn.onclick = async ()=>{
                    const t=(msg.value||'').trim(); if(!t) return; append('You', t); msg.value='';
                    const res = await rpc('/grok/chat_http', {message:t, session_id:sid});
                    append('Assistant', res.reply||'');
                };
            })();
            </script></body></html>""".replace("%(sid)s", str(values.get("session_id")))
            return request.make_response(html, headers=[("Content-Type","text/html; charset=utf-8")])

    @http.route("/grok/config", type="http", auth="user", website=False)
    def grok_config(self, **kw):
        values = {"user_name": request.env.user.display_name}
        try:
            return request.render("grok_odoo_assistant_pro17_clean.config_page", values)
        except Exception as e:
            html = f"<html><body style='font-family:system-ui;max-width:920px;margin:2rem auto'><h2>Settings (fallback)</h2><div style='color:#b00'>Template render failed: {e}</div></body></html>"
            return request.make_response(html, headers=[("Content-Type","text/html; charset=utf-8")])

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