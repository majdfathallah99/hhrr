import json
import re
import requests
from odoo import http, _, fields
from odoo.http import request
from markupsafe import Markup, escape

# --- Helpers ---

def _detect_lang(text):
    if not text:
        return "ar"
    # Simple heuristic: if it contains Arabic letters, mark ar; otherwise en
    return "ar" if re.search(r"[\u0600-\u06FF]", text) else "en"

def _get_llm_config():
    ICP = request.env["ir.config_parameter"].sudo()
    return {
        "provider": ICP.get_param("grok.provider") or "xai",
        "endpoint": ICP.get_param("grok.endpoint") or "",
        "model": ICP.get_param("grok.model") or "grok-2-latest",
        "api_key": ICP.get_param("grok.api_key") or "",
        "temperature": float(ICP.get_param("grok.temperature") or 0.2),
        "allowed_models": [m.strip() for m in (ICP.get_param("grok.allowed_models") or "").split(",") if m.strip()],
    }

def _llm_headers(cfg):
    key = cfg["api_key"]
    return {
        "Authorization": f"Bearer {key}" if key else "",
        "Content-Type": "application/json",
    }

def _llm_base(cfg):
    # Guess defaults by provider
    if cfg["provider"] == "xai":
        return "https://api.x.ai"
    if cfg["provider"] == "groq":
        return "https://api.groq.com/openai"
    if cfg["provider"] == "openai":
        return "https://api.openai.com"
    if cfg["endpoint"]:
        return cfg["endpoint"].rstrip("/")
    return "https://api.openai.com"

SYSTEM_PROMPT = """
You are Grok Odoo Assistant Pro, a helpful bilingual (Arabic + English) assistant for Odoo.
Style rules:
- Speak the user's language: Arabic if they write Arabic, English if they write English. You may mix if the user mixes.
- Be concise, friendly, and natural — like a real person. Avoid robotic or stilted phrases.
- Never output raw tool markup. If you plan an action, summarize it in natural language and wait for confirmation.
- For actions, return a JSON tool call ONLY when the user explicitly approves.
- When the user asks for actions, confirm key details (products, quantities, partner, prices) and show a short summary before execution.
- If unsure, ask a brief clarifying question.
Capabilities:
- Search, create, and update Odoo records (products, partners, sale/purchase orders) via the provided tools.
- Use the provided tools only when asked and approved.
""".strip()

TOOL_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "create_product",
            "description": "Create a product (product.template).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "default_code": {"type": "string"},
                    "list_price": {"type": "number"},
                    "standard_price": {"type": "number"},
                    "categ_id": {"type": "integer"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_partner",
            "description": "Create a contact (res.partner).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_sale_order",
            "description": "Create a sale order with lines. Lines are provided as (product_code_or_name, quantity, price).",
            "parameters": {
                "type": "object",
                "properties": {
                    "partner_name": {"type": "string"},
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item": {"type": "string"},
                                "qty": {"type": "number"},
                                "price": {"type": "number"}
                            },
                            "required": ["item","qty"]
                        }
                    }
                },
                "required": ["partner_name","lines"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_purchase_order",
            "description": "Create a purchase order with lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "partner_name": {"type": "string"},
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item": {"type": "string"},
                                "qty": {"type": "number"},
                                "price": {"type": "number"}
                            },
                            "required": ["item","qty"]
                        }
                    }
                },
                "required": ["partner_name","lines"]
            }
        }
    }
]

# --- Tool executor (server-side) ---

def _create_product(values):
    env = request.env
    tmpl = env["product.template"].sudo().create({
        "name": values.get("name"),
        "default_code": values.get("default_code"),
        "list_price": values.get("list_price") or 0.0,
        "standard_price": values.get("standard_price") or 0.0,
        "categ_id": values.get("categ_id") or False,
    })
    return {"id": tmpl.id, "name": tmpl.name}

def _find_product(item):
    env = request.env
    Product = env["product.product"].sudo()
    # try code
    prod = Product.search([("default_code","=", item)], limit=1)
    if not prod:
        prod = Product.search([("name","ilike", item)], limit=1)
    return prod

def _create_sale_order(values):
    env = request.env
    partner = env["res.partner"].sudo().search([("name","=", values.get("partner_name"))], limit=1)
    if not partner:
        partner = env["res.partner"].sudo().create({"name": values.get("partner_name")})
    order = env["sale.order"].sudo().create({"partner_id": partner.id})
    for l in values.get("lines") or []:
        prod = _find_product(l.get("item"))
        if not prod:
            continue
        env["sale.order.line"].sudo().create({
            "order_id": order.id,
            "product_id": prod.id,
            "product_uom_qty": l.get("qty") or 1.0,
            "price_unit": l.get("price") or prod.lst_price,
        })
    return {"id": order.id, "name": order.name}

def _create_purchase_order(values):
    env = request.env
    partner = env["res.partner"].sudo().search([("name","=", values.get("partner_name"))], limit=1)
    if not partner:
        partner = env["res.partner"].sudo().create({"name": values.get("partner_name")})
    order = env["purchase.order"].sudo().create({"partner_id": partner.id})
    for l in values.get("lines") or []:
        prod = _find_product(l.get("item"))
        if not prod:
            continue
        env["purchase.order.line"].sudo().create({
            "order_id": order.id,
            "product_id": prod.id,
            "product_qty": l.get("qty") or 1.0,
            "price_unit": l.get("price") or prod.standard_price,
            "name": prod.name,
        })
    return {"id": order.id, "name": order.name}

TOOL_IMPL = {
    "create_product": _create_product,
    "create_partner": lambda vals: {"id": request.env["res.partner"].sudo().create(vals).id, "name": vals.get("name")},
    "create_sale_order": _create_sale_order,
    "create_purchase_order": _create_purchase_order,
}

# --- Controllers ---

class GrokController(http.Controller):

    # Main UI (any internal user)
    @http.route("/grok/ui", type="http", auth="user", website=True, csrf=False)
    def grok_ui(self, **kw):
        # create session
        session = request.env["grok.assistant.session"].sudo().create({})
        return request.render("grok_odoo_assistant_pro18_fi.ui_page", {
            "session_id": session.id,
            "user_name": request.env.user.display_name,
        })

    # Admin-only config UI
    @http.route("/grok/config", type="http", auth="user", website=True, csrf=False)
    def grok_config(self, **kw):
        if not request.env.user.has_group("base.group_system"):
            return request.not_found()
        settings = request.env["res.config.settings"].sudo().create({})
        values = settings.get_values()
        return request.render("grok_odoo_assistant_pro18_fi.config_page", values)

    @http.route("/grok/config/save", type="http", auth="user", methods=["POST"], csrf=False)
    def grok_config_save(self, **post):
        if not request.env.user.has_group("base.group_system"):
            return request.not_found()
        settings = request.env["res.config.settings"].sudo().create({})
        settings.write({
            "grok_provider": post.get("grok_provider"),
            "grok_endpoint": post.get("grok_endpoint"),
            "grok_model": post.get("grok_model"),
            "grok_api_key": post.get("grok_api_key"),
            "grok_temperature": float(post.get("grok_temperature") or 0.2),
            "grok_allowed_models": post.get("grok_allowed_models"),
        })
        settings.set_values()
        return request.redirect("/grok/config")

    # Chat endpoint
    @http.route("/grok/chat_http", type="json", auth="user", csrf=False)
    def grok_chat(self, message, session_id=None, approve=False, tool_payload=None):
        env = request.env
        Session = env["grok.assistant.session"].sudo()
        Message = env["grok.assistant.message"].sudo()

        if not session_id:
            session = Session.create({})
        else:
            session = Session.browse(int(session_id))
            if not session.exists():
                session = Session.create({})

        lang = _detect_lang(message or "")
        Message.create({
            "session_id": session.id,
            "role": "user",
            "content": message or "",
            "detected_lang": lang,
        })
        session.last_lang = lang

        # If a tool_payload comes back approved, execute it
        if approve and tool_payload:
            try:
                payload = json.loads(tool_payload)
                tool_name = payload.get("name")
                args = payload.get("arguments") or {}
                impl = TOOL_IMPL.get(tool_name)
                if not impl:
                    raise ValueError("Unknown tool")
                result = impl(args)
                reply = _("✅ Done. Result: %s") % (json.dumps(result, ensure_ascii=False))
            except Exception as e:
                reply = _("❌ Failed: %s") % (str(e))
            Message.create({
                "session_id": session.id,
                "role": "assistant",
                "content": reply,
                "detected_lang": lang,
            })
            return {"reply": reply, "session_id": session.id, "lang": lang}

        # Call LLM
        cfg = _get_llm_config()
        base = _llm_base(cfg)
        headers = _llm_headers(cfg)

        # Build chat history
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        hist = Message.search([("session_id","=",session.id)], order="id asc", limit=20)
        for m in hist:
            msgs.append({"role": m.role, "content": m.content})

        payload = {
            "model": cfg["model"],
            "temperature": cfg["temperature"],
            "messages": msgs,
            "tools": TOOL_SPEC,
            "tool_choice": "auto",
        }

        try:
            resp = requests.post(f"{base}/v1/chat/completions", headers=headers, json=payload, timeout=60)
            data = resp.json()
        except Exception as e:
            data = {"error": str(e)}

        # Parse response
        reply = ""
        pending_tool = None
        if isinstance(data, dict) and data.get("choices"):
            choice = data["choices"][0]
            msg = choice.get("message") or {}
            reply = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []
            if tool_calls:
                tc = tool_calls[0]
                pending_tool = {"name": tc["function"]["name"], "arguments": json.loads(tc["function"].get("arguments") or "{}")}
        elif data.get("error"):
            reply = _("❌ LLM Error: %s") % data["error"]
        else:
            reply = _("لم أفهم. حاول مجددًا.") if lang == "ar" else "I didn't understand. Please try again."

        # Sanitize trashy outputs like <<COMMAND>>
        reply = re.sub(r"<<.*?>>", "", reply).strip()

        # If there's a pending tool call, don't execute yet. Return a confirmation card.
        if pending_tool:
            summary = _("Proposed action: %s") % (json.dumps(pending_tool, ensure_ascii=False))
            natural = _("أرغب بتنفيذ العملية التالية. هل تؤكد؟") if lang=="ar" else "I can do this. Do you want me to proceed?"
            final_reply = f"{reply}\n\n---\n{summary}\n{natural}"
            Message.create({
                "session_id": session.id,
                "role": "assistant",
                "content": final_reply,
                "detected_lang": lang,
            })
            return {"reply": final_reply, "session_id": session.id, "lang": lang, "pending_tool": json.dumps(pending_tool, ensure_ascii=False)}

        Message.create({
            "session_id": session.id,
            "role": "assistant",
            "content": reply,
            "detected_lang": lang,
        })
        return {"reply": reply, "session_id": session.id, "lang": lang}
