
from odoo import http
from odoo.http import request

TOOLS_MODEL = "ai.business.tools.core"

class AIAssistantController(http.Controller):
    """Stateful assistant with SMART fast-paths and diagnostic-safe responses."""

    # ---------- session helpers ----------
    def _get_history(self):
        hist = request.session.get("ai_chat_history") or []
        if not isinstance(hist, list):
            hist = []
        return hist

    def _save_history(self, hist):
        if len(hist) > 32:
            hist = hist[-32:]
        request.session["ai_chat_history"] = hist
        request.session.modified = True

    # ---------- diagnostics helper ----------
    def _json_error(self, err):
        import json, traceback
        try:
            return json.dumps({"error": str(err), "trace": traceback.format_exc()}, ensure_ascii=False)
        except Exception:
            return '{"error":"unserializable error"}'

    # ---------- fast-path helpers (no-LLM) ----------
    def _ensure_partner(self, name: str, as_vendor=False):
        Partner = request.env["res.partner"].sudo()
        dom = [("name", "ilike", name)]
        dom.append(("supplier_rank", ">", 0) if as_vendor else ("customer_rank", ">", 0))
        p = Partner.search(dom, limit=1)
        if p:
            return p
        vals = {"name": name}
        if as_vendor:
            vals["supplier_rank"] = 1
        else:
            vals["customer_rank"] = 1
        try:
            return Partner.create(vals)
        except Exception:
            return Partner.search([("name", "ilike", name)], limit=1)

    def _ensure_product(self, name: str):
        Product = request.env["product.product"].sudo()
        p = Product.search([("name", "ilike", name)], limit=1)
        if p:
            return p
        try:
            Uom = request.env["uom.uom"].sudo()
            unit = Uom.search([("uom_type", "=", "reference")], limit=1)
            vals = {
                "name": name,
                "detailed_type": "product",
                "uom_id": unit.id or False,
                "uom_po_id": unit.id or False,
            }
            return Product.create(vals)
        except Exception:
            return Product.search([("name", "ilike", name)], limit=1)

    def _parse_qty_and_product(self, message: str):
        import re
        m = re.search(r"(\d+)[^\w]+(.+)", message, flags=re.I)
        if not m:
            return None, None
        qty = int(m.group(1))
        prod = m.group(2).strip()
        for stop in [" for ", " from ", " to ", " with ", " of "]:
            idx = prod.lower().find(stop)
            if idx > 0:
                prod = prod[:idx].strip()
        return qty, prod

    def _fastpath(self, message: str):
        import re
        msg = message.lower()

        # Create Sales Order
        if "create" in msg and ("sale order" in msg or "sales order" in msg or " so" in msg or msg.endswith(" so")):
            customer = None
            mfor = re.search(r"for\s+([\w .'-]+)", message, flags=re.I)
            if mfor:
                customer = mfor.group(1).strip()
            if not customer:
                customer = request.session.get("ai_last_customer")

            qty, prod_name = self._parse_qty_and_product(message) if any(w in msg for w in [" sell ", " contains ", " item ", " product "]) else (None, None)
            if not qty or not prod_name:
                m = re.search(r"sell .*?(\d+)\s+([\w .'-]+)", message, flags=re.I)
                if m:
                    qty = int(m.group(1))
                    prod_name = m.group(2).strip()

            if customer and qty and prod_name:
                from odoo import fields
                partner = self._ensure_partner(customer, as_vendor=False)
                product = self._ensure_product(prod_name)
                so = request.env["sale.order"].sudo().create({
                    "partner_id": partner.id,
                    "date_order": fields.Datetime.now(),
                    "order_line": [(0, 0, {
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "name": product.name,
                        "price_unit": product.lst_price or 0.0,
                    })],
                })
                request.session["ai_last_customer"] = partner.name
                return {"text": f"Created Sales Order {so.name} for {partner.display_name}: {qty} × {product.display_name}. Status: {so.state}."}

            if customer and not request.session.get("ai_last_customer"):
                request.session["ai_last_customer"] = customer
            return None

        # Create Purchase Order
        if "create" in msg and ("purchase order" in msg or " po" in msg or msg.endswith(" po")):
            vendor = None
            mfrom = re.search(r"from\s+([\w .'-]+)", message, flags=re.I)
            if mfrom:
                vendor = mfrom.group(1).strip()
            if not vendor:
                vendor = request.session.get("ai_last_vendor")

            qty, prod_name = self._parse_qty_and_product(message)
            if not qty or not prod_name:
                m = re.search(r"buy .*?(\d+)\s+([\w .'-]+)", message, flags=re.I)
                if m:
                    qty = int(m.group(1))
                    prod_name = m.group(2).strip()

            if vendor and qty and prod_name:
                from odoo import fields
                partner = self._ensure_partner(vendor, as_vendor=True)
                product = self._ensure_product(prod_name)
                po = request.env["purchase.order"].sudo().create({
                    "partner_id": partner.id,
                    "date_order": fields.Datetime.now(),
                    "order_line": [(0, 0, {
                        "product_id": product.id,
                        "name": product.name,
                        "product_qty": qty,
                        "price_unit": product.standard_price or 0.0,
                        "product_uom": product.uom_po_id.id or product.uom_id.id,
                        "date_planned": fields.Datetime.now(),
                    })],
                })
                request.session["ai_last_vendor"] = partner.name
                return {"text": f"Created Purchase Order {po.name} from {partner.display_name}: {qty} × {product.display_name}. Status: {po.state}."}

            if vendor and not request.session.get("ai_last_vendor"):
                request.session["ai_last_vendor"] = vendor
            return None

        return None

    # ---------- core logic ----------
    def _core_ai_logic(self, message: str):
        import json, requests

        # append user message
        hist = self._get_history()
        hist.append({"role": "user", "content": message})
        self._save_history(hist)

        # fast-path (no LLM)
        fp = self._fastpath(message)
        if fp:
            hist = self._get_history()
            hist.append({"role": "assistant", "content": fp.get("text", "(done)")})
            self._save_history(hist)
            return fp

        if message and message.strip().lower() in ("hi", "hello", "hey"):
            g = "Hi! Ask me about your Odoo data or tell me to create/update records (e.g., create a sales order …)."
            hist.append({"role": "assistant", "content": g})
            self._save_history(hist)
            return {"text": g, "message": g, "tool_calls": [], "tool_results": []}

        ICP = request.env["ir.config_parameter"].sudo()
        provider = (ICP.get_param("ai_business_assistant.ai_provider") or "openai").strip()
        api_key = (ICP.get_param("ai_business_assistant.ai_api_key") or "").strip()
        model = (ICP.get_param("ai_business_assistant.ai_model") or "gpt-4o-mini").strip()
        base_url = (ICP.get_param("ai_business_assistant.ai_base_url") or "").strip()
        if not base_url:
            if provider == "groq":
                base_url = "https://api.groq.com/openai/v1"
            elif provider == "ollama":
                base_url = "http://localhost:11434/v1"
            else:
                base_url = "https://api.openai.com/v1"
        if not api_key:
            return {"error": "Missing API key"}

        # Optional tools
        tool_schemas = []
        try:
            ToolModel = request.env[TOOLS_MODEL].sudo()
            tool_schemas = ToolModel.tool_schemas()
        except Exception:
            tool_schemas = []

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = base_url.rstrip("/") + "/chat/completions"
        sys_prompt = (
            "You are an Odoo business assistant. Maintain conversation context across messages. "
            "Only call write/create/delete tools when the user explicitly requests it and after you have enough details "
            "(vendor for PO vs customer for SO, lines). Ask concise follow-up questions to gather missing details. "
            "Never invent IDs, partners, or products. For domains and lines, output proper JSON arrays, not strings. "
            "Keep answers short and plain."
        )

        payload = {
            "model": model,
            "messages": [{"role": "system", "content": sys_prompt}] + self._get_history(),
            "temperature": 0.2,
        }
        if tool_schemas:
            payload["tools"] = tool_schemas
            payload["tool_choice"] = "auto"

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            jd = r.json()
        except Exception as e:
            return {"error": f"Upstream call failed: {e}"}
        if r.status_code >= 400:
            return {"error": f"Upstream error {r.status_code}: {jd}"}

        choices = jd.get("choices") or []
        if not choices:
            txt = "(no content)"
            hist = self._get_history()
            hist.append({"role": "assistant", "content": txt})
            self._save_history(hist)
            return {"text": txt, "message": txt, "tool_calls": [], "tool_results": []}
        msg = choices[0].get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        tool_results = []

        if tool_calls and tool_schemas:
            import json as _json, traceback
            try:
                ToolModel = request.env[TOOLS_MODEL].sudo()
            except Exception as e:
                text = "(tool model unavailable, switching to plain chat)"
                hist = self._get_history()
                hist.append({"role": "assistant", "content": text})
                self._save_history(hist)
                return {"text": text, "message": text, "tool_calls": [], "tool_results": []}

            for tc in tool_calls[:5]:
                fn = (tc.get("function") or {}).get("name")
                args_str = (tc.get("function") or {}).get("arguments") or "{}"
                try:
                    args = _json.loads(args_str)
                except Exception:
                    args = {}
                try:
                    res = ToolModel.execute_tool(fn, args)
                    tool_results.append({"tool_call_id": tc.get("id"), "name": fn, "content": res})
                except Exception as e:
                    tool_results.append({"tool_call_id": tc.get("id"), "name": fn, "error": str(e)})

            tool_msgs = [{
                "role": "tool",
                "tool_call_id": tr["tool_call_id"],
                "name": tr["name"],
                "content": (_json.dumps(tr.get("content", tr.get("error", "")), ensure_ascii=False))
            } for tr in tool_results]

            hist2 = self._get_history()
            hist2.append(msg)
            hist2.extend(tool_msgs)
            self._save_history(hist2)

            payload2 = {
                "model": model,
                "messages": [{"role": "system", "content": sys_prompt}] + hist2,
                "temperature": 0.2,
            }
            try:
                r2 = requests.post(url, headers=headers, json=payload2, timeout=60)
                jd2 = r2.json()
            except Exception as e:
                txt = f"(tool-call roundtrip failed: {e})"
                hist = self._get_history()
                hist.append({"role": "assistant", "content": txt})
                self._save_history(hist)
                return {"text": txt, "message": txt, "tool_calls": tool_calls, "tool_results": tool_results}
            if r2.status_code >= 400:
                txt = f"Upstream error {r2.status_code}: {jd2}"
                hist = self._get_history()
                hist.append({"role": "assistant", "content": txt})
                self._save_history(hist)
                return {"text": txt, "message": txt, "tool_calls": tool_calls, "tool_results": tool_results}

            choices2 = jd2.get("choices") or []
            final_msg = choices2[0].get("message", {}) if choices2 else {}
            text = final_msg.get("content") or "(empty)"
            hist = self._get_history()
            hist.append({"role": "assistant", "content": text})
            self._save_history(hist)
            return {"text": text, "message": text, "tool_calls": tool_calls, "tool_results": tool_results}

        text = msg.get("content") or "(empty)"
        hist = self._get_history()
        hist.append({"role": "assistant", "content": text})
        self._save_history(hist)
        return {"text": text, "message": text, "tool_calls": [], "tool_results": []}

    # ---------- routes ----------
    @http.route("/ai_assistant/query_http", type="http", auth="user", csrf=False, methods=["POST", "GET"])
    def ai_query_http(self, **kw):
        import json as _json
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True)
            message = None
            if raw:
                try:
                    body = _json.loads(raw)
                    message = body.get("message")
                except Exception:
                    pass
            if not message:
                message = request.httprequest.args.get("message")
            if not message:
                return request.make_response('{"error":"Missing parameter: \'message\'"}',
                                             headers=[("Content-Type", "application/json")], status=200)
            res = self._core_ai_logic(message)
            try:
                body = _json.dumps(res, ensure_ascii=False)
            except Exception:
                body = '{"text":"(serialization error)"}'
            return request.make_response(body, headers=[("Content-Type", "application/json")], status=200)
        except Exception as e:
            return request.make_response(self._json_error(e), headers=[("Content-Type", "application/json")], status=200)

    @http.route("/ai_assistant/query_rpc", type="json", auth="user", csrf=False, methods=["POST", "GET"])
    def ai_query_json(self, message=None, **kw):
        try:
            if not message:
                message = (request.jsonrequest or {}).get("message")
            if not message:
                return {"error": "Missing parameter: 'message'"}
            return self._core_ai_logic(message)
        except Exception as e:
            import traceback
            return {"error": str(e), "trace": traceback.format_exc()}

    @http.route("/ai_assistant_minimal", type="http", auth="user", csrf=False, methods=["GET"])
    def ai_minimal_page(self, **kw):
        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AI Business Assistant</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root{--primary:#3b82f6;--bg:#fff;--muted:#6b7280;--ring:#93c5fd;}
  *{box-sizing:border-box}
  body{font-family:Inter,system-ui,Arial,sans-serif;margin:28px;background:var(--bg)}
  .wrap{max-width:960px;margin:0 auto}
  h1{font-size:28px;margin:0 0 16px}
  #log{border:1px solid #e5e7eb;padding:12px;height:380px;overflow:auto;border-radius:10px;background:#fafafa}
  #msg{width:100%;padding:12px;border-radius:10px;border:1px solid #d1d5db;margin-top:10px;font-size:14px;outline:none}
  #msg:focus{box-shadow:0 0 0 3px var(--ring)}
  .row{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
  button{padding:10px 16px;border-radius:10px;border:1px solid #d1d5db;background:#fff;cursor:pointer}
  button.primary{background:var(--primary);color:white;border-color:var(--primary)}
  button:disabled{opacity:.6;cursor:not-allowed}
  .item{margin:6px 0}
  .you{color:#111}
  .ai{color:#0b5}
  .err{color:#c00}
  .meta{color:var(--muted);font-size:12px}
  .pill{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;border:1px solid #d1d5db;background:#fff;font-size:12px}
  .pill.on{background:#ecfdf5;border-color:#34d399}
  .status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;background:#9ca3af}
  .status-dot.on{background:#10b981}
</style>
</head>
<body>
  <div class="wrap">
    <h1>AI Business Assistant</h1>
    <div id="log" aria-live="polite"></div>
    <textarea id="msg" rows="3" placeholder="Ask: e.g., how many products do I have?"></textarea>
    <div class="row">
      <button id="sendBtn" class="primary">Send</button>
      <button id="resetBtn">Reset</button>
      <button id="pttBtn" title="Hold to talk (push-to-talk)">🎤 Hold to Talk</button>
      <span class="pill" id="voiceToggle"><span class="status-dot" id="voiceDot"></span><span id="voiceText">Voice Off</span></span>
    </div>
    <p class="meta">This page calls <code>/ai_assistant/query_http</code>. Voice uses your browser's Web Speech API.</p>
  </div>
<script>
// ---- helpers ----
const log = document.getElementById('log');
const msg = document.getElementById('msg');
const sendBtn = document.getElementById('sendBtn');
const resetBtn = document.getElementById('resetBtn');
const pttBtn = document.getElementById('pttBtn');
const voiceToggle = document.getElementById('voiceToggle');
const voiceDot = document.getElementById('voiceDot');
const voiceText = document.getElementById('voiceText');

function addLine(cls, text){
  const d = document.createElement('div');
  d.className = 'item '+cls;
  d.textContent = text;
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
}

async function ask(explicitText){
  const q = (explicitText ?? msg.value).trim();
  if(!q) return;
  addLine('you', 'You: '+q);
  msg.value='';
  try{
    const res = await fetch('/ai_assistant/query_http', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:q})
    });
    const txt = await res.text();
    let jd=null; try{ jd = JSON.parse(txt); }catch{}
    const reply = (jd && (jd.text||jd.message)) ? (jd.text||jd.message) : (jd && jd.error ? 'Error: '+jd.error : txt);
    addLine(jd && jd.error ? 'err' : 'ai', 'Assistant: '+reply);
    // TTS
    if(isVoiceOn() && 'speechSynthesis' in window){
      const u = new SpeechSynthesisUtterance(reply);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    }
  }catch(e){ addLine('err', 'Network error: '+e); }
}

// ---- voice ----
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recog = null;
let listening = false;

function isVoiceOn(){ return localStorage.getItem('ai_voice_on') === '1'; }
function setVoiceOn(on){
  localStorage.setItem('ai_voice_on', on ? '1' : '0');
  if(on){ voiceToggle.classList.add('on'); voiceDot.classList.add('on'); voiceText.textContent='Voice On'; }
  else{ voiceToggle.classList.remove('on'); voiceDot.classList.remove('on'); voiceText.textContent='Voice Off'; }
}
setVoiceOn(isVoiceOn());

voiceToggle.addEventListener('click', ()=> setVoiceOn(!isVoiceOn()));

function ensureRecog(){
  if(recog || !SR) return;
  recog = new SR();
  recog.continuous = false;
  recog.interimResults = true;
  recog.lang = (navigator.language || 'en-US');
  let interim = '';
  recog.onresult = (ev)=>{
    let finalTxt='';
    for(let i=ev.resultIndex;i<ev.results.length;i++){
      const r = ev.results[i];
      if(r.isFinal){ finalTxt += r[0].transcript; }
      else { interim += r[0].transcript; }
    }
    if(interim){ msg.value = (msg.value.trim() + ' ' + interim).trim(); interim=''; }
    if(finalTxt){ msg.value = (msg.value.trim() + ' ' + finalTxt).trim(); }
  };
  recog.onerror = (e)=>{ listening=false; pttBtn.disabled=false; addLine('err','Mic error: '+e.error); };
  recog.onend = ()=>{
    if(listening){
      // push-to-talk ended -> send if we have text
      listening=false;
      pttBtn.disabled=false;
      if(msg.value.trim()){ ask(); }
    }
  };
}

pttBtn.addEventListener('mousedown', ()=>{
  if(!isVoiceOn()){ addLine('meta','(Enable Voice first)'); return; }
  if(!SR){ addLine('err', 'This browser does not support SpeechRecognition.'); return; }
  ensureRecog();
  try{ window.speechSynthesis && window.speechSynthesis.cancel(); }catch{}
  listening=true; pttBtn.disabled=true;
  msg.placeholder='Listening…';
  try{ recog.start(); }catch(e){ /* ignore start twice errors */ }
});
['mouseup','mouseleave','touchend','touchcancel'].forEach(evt=>{
  pttBtn.addEventListener(evt, ()=>{
    if(recog && listening){
      try{ recog.stop(); }catch{}
    }
  });
});

sendBtn.addEventListener('click', ()=> ask());
msg.addEventListener('keydown', (e)=>{
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); ask(); }
});
resetBtn.addEventListener('click', async ()=>{
  await fetch('/ai_assistant/reset', {method:'POST'});
  addLine('meta','(chat reset)');
});
</script>
</body>
</html>"""
        return request.make_response(html, headers=[("Content-Type","text/html")])