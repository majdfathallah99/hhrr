# -*- coding: utf-8 -*-
import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an Odoo assistant. Respond in the user's language.\n"
    "When the user asks for data changes or retrievals, output a COMMAND block:\n"
    "<<COMMAND>>\n"
    "action=<create|write|read|create_sale_order|add_sale_order_lines|create_purchase_order|add_purchase_order_lines|create_product|create_partner>\n"
    "model=<odoo.model> (only for create/write/read)\n"
    "id=<record_id> (for write, add_*_lines)\n"
    "values=<k=v;...> (for create/write or specialized actions)\n"
    "lines=<item1|item2|...> each item NAME*QTY[@PRICE] (e.g., 'Blue Pen*3@12.5' or 'PEN-001*2')\n"
    "search_name=<text> (for read)\n"
    "<<END>>\n"
    "Prefer create_product for new products and create_sale_order/create_purchase_order for orders."
)

class GrokAssistantSession(models.Model):
    _name = "grok.assistant.session"
    _description = "Grok Assistant Session"
    _order = "create_date desc"

    name = fields.Char(default=lambda self: _("Session"))
    message_ids = fields.One2many("grok.assistant.message", "session_id", string="Messages")
    active = fields.Boolean(default=True)

    # ----- Provider plumbing -----
    def _allowed_models(self):
        params = self.env['ir.config_parameter'].sudo()
        raw = params.get_param('grok_odoo_assistant.allowed_models', '') or ''
        names = [n.strip() for n in raw.split(',') if n.strip()]
        return [n for n in names if n in self.env]

    def _build_endpoint(self):
        params = self.env['ir.config_parameter'].sudo()
        provider = (params.get_param('grok_odoo_assistant.provider', 'xai') or 'xai').lower()
        custom = params.get_param('grok_odoo_assistant.endpoint_url', '') or ''
        if provider == 'xai':
            return 'https://api.x.ai/v1/chat/completions'
        if provider == 'groq':
            return 'https://api.groq.com/openai/v1/chat/completions'
        return custom or 'https://api.x.ai/v1/chat/completions'

    def _call_llm(self, user_text):
        params = self.env['ir.config_parameter'].sudo()
        api_key = params.get_param('grok_odoo_assistant.api_key') or ''
        if not api_key:
            # user-facing message rather than exception
            return _("لم يتم ضبط مفتاح API. من فضلك أدخل المفتاح في /grok/config.")
        model = params.get_param('grok_odoo_assistant.model', 'grok-4-latest') or 'grok-4-latest'
        try:
            temp = float(params.get_param('grok_odoo_assistant.temperature', '0.0') or 0.0)
        except Exception:
            temp = 0.0
        endpoint = self._build_endpoint()

        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        last_msgs = self.message_ids.sorted(key=lambda m: m.create_date)[-10:]
        for m in last_msgs:
            messages.append({'role': m.role, 'content': m.content})
        messages.append({'role': 'user', 'content': user_text})

        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {'messages': messages, 'model': model, 'stream': False, 'temperature': temp}

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        except Exception as e:
            return _("تعذّر الاتصال بالمزوّد: %s") % e
        if resp.status_code >= 300:
            # show body so the user can diagnose
            return _("خطأ من واجهة النموذج: %s") % resp.text

        # Defensive JSON handling
        try:
            data = resp.json()
        except Exception:
            return _("لم أتمكن من فهم ردّ المزود (JSON غير صالح). راجع /grok/config.")

        content = ""
        try:
            content = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
        except Exception:
            content = ""
        if not content:
            content = _("لم أتلقَّ ردًا من نموذج الذكاء الاصطناعي. تحقق من الإعدادات في /grok/config (المزوّد/الموديل/المفتاح).")
        return content

    # ---------- Helpers ----------
    def _find_partner(self, text):
        Partner = self.env['res.partner'].sudo()
        if not text:
            return None
        rec = Partner.search([('name', '=', text)], limit=1)
        if not rec:
            rec = Partner.search([('name', 'ilike', text)], limit=1)
        return rec or None

    def _find_product(self, token):
        Product = self.env['product.product'].sudo()
        if not token:
            return None
        token = token.strip().strip('"').strip("'")
        rec = Product.search([('default_code', '=', token)], limit=1)
        if rec:
            return rec
        rec = Product.search([('name', '=', token)], limit=1)
        if rec:
            return rec
        rec = Product.search([('name', 'ilike', token)], limit=1)
        return rec or None

    def _parse_lines(self, lines_text):
        items = []
        if not lines_text:
            return items
        for raw in [x.strip() for x in lines_text.split('|') if x.strip()]:
            name = raw; qty = 1.0; price = None
            if '*' in raw:
                name, rest = raw.split('*', 1)
                name = name.strip()
                if '@' in rest:
                    qstr, pstr = rest.split('@', 1)
                    try: qty = float(qstr.strip())
                    except Exception: qty = 1.0
                    try: price = float(pstr.strip())
                    except Exception: price = None
                else:
                    try: qty = float(rest.strip())
                    except Exception: qty = 1.0
            prod = self._find_product(name)
            items.append({'token': name, 'product': prod, 'qty': qty, 'price': price})
        return items

    # ---------- Specialized actions ----------
    def _create_sale_order(self, values):
        partner_text = values.get('partner') or values.get('customer') or values.get('partner_id')
        partner = None
        if isinstance(partner_text, (int, float)):
            partner = self.env['res.partner'].sudo().browse(int(partner_text))
        else:
            partner = self._find_partner(str(partner_text)) if partner_text else None
        if not partner:
            return "Missing or unknown partner for sale order."
        so = self.env['sale.order'].sudo().create({'partner_id': partner.id})
        lines = self._parse_lines(values.get('lines') or '')
        created = 0
        for l in lines:
            prod = l['product']
            if not prod:
                continue
            vals = {'order_id': so.id, 'product_id': prod.id, 'product_uom_qty': l['qty'] or 1.0}
            if l['price'] is not None:
                vals['price_unit'] = l['price']
            self.env['sale.order.line'].sudo().create(vals)
            created += 1
        return f"Created sale.order {so.name} (ID {so.id}) with {created} line(s)."

    def _add_sale_order_lines(self, values):
        so_id = int(values.get('id') or 0)
        if not so_id:
            return "add_sale_order_lines needs id"
        so = self.env['sale.order'].sudo().browse(so_id)
        if not so.exists():
            return f"Sale order {so_id} not found."
        lines = self._parse_lines(values.get('lines') or '')
        created = 0
        for l in lines:
            prod = l['product']
            if not prod:
                continue
            vals = {'order_id': so.id, 'product_id': prod.id, 'product_uom_qty': l['qty'] or 1.0}
            if l['price'] is not None:
                vals['price_unit'] = l['price']
            self.env['sale.order.line'].sudo().create(vals)
            created += 1
        return f"Added {created} line(s) to sale.order ID {so.id}."

    def _create_purchase_order(self, values):
        partner_text = values.get('partner') or values.get('vendor') or values.get('partner_id')
        partner = None
        if isinstance(partner_text, (int, float)):
            partner = self.env['res.partner'].sudo().browse(int(partner_text))
        else:
            partner = self._find_partner(str(partner_text)) if partner_text else None
        if not partner:
            return "Missing or unknown vendor for purchase order."
        po = self.env['purchase.order'].sudo().create({'partner_id': partner.id})
        lines = self._parse_lines(values.get('lines') or '')
        created = 0
        for l in lines:
            prod = l['product']
            if not prod:
                continue
            vals = {'order_id': po.id, 'product_id': prod.id, 'product_qty': l['qty'] or 1.0}
            if l['price'] is not None:
                vals['price_unit'] = l['price']
            self.env['purchase.order.line'].sudo().create(vals)
            created += 1
        return f"Created purchase.order {po.name} (ID {po.id}) with {created} line(s)."

    def _add_purchase_order_lines(self, values):
        po_id = int(values.get('id') or 0)
        if not po_id:
            return "add_purchase_order_lines needs id"
        po = self.env['purchase.order'].sudo().browse(po_id)
        if not po.exists():
            return f"Purchase order {po_id} not found."
        lines = self._parse_lines(values.get('lines') or '')
        created = 0
        for l in lines:
            prod = l['product']
            if not prod:
                continue
            vals = {'order_id': po.id, 'product_id': prod.id, 'product_qty': l['qty'] or 1.0}
            if l['price'] is not None:
                vals['price_unit'] = l['price']
            self.env['purchase.order.line'].sudo().create(vals)
            created += 1
        return f"Added {created} line(s) to purchase.order ID {po.id}."

    def _create_product(self, values):
        name = values.get('name') or values.get('product_name')
        if not name:
            return "Product needs a name."
        vals = {'name': name}
        if values.get('default_code'):
            vals['default_code'] = values.get('default_code')
        if values.get('list_price'):
            try: vals['list_price'] = float(values.get('list_price'))
            except Exception: pass
        if values.get('standard_price'):
            try: vals['standard_price'] = float(values.get('standard_price'))
            except Exception: pass
        if values.get('type') in ('consu','product','service'):
            vals['type'] = values.get('type')
        tmpl = self.env['product.template'].sudo().create(vals)
        prod = tmpl.product_variant_id
        return f"Created product.template ID {tmpl.id} / product.product ID {prod.id}."

    def _create_partner(self, values):
        name = values.get('name') or values.get('partner') or values.get('customer') or values.get('vendor')
        if not name:
            return "Partner needs a name."
        vals = {'name': name}
        for k in ('phone','email','mobile','vat','street','city','zip','country_id','company_name'):
            if values.get(k):
                vals[k] = values.get(k)
        rec = self.env['res.partner'].sudo().create(vals)
        return f"Created res.partner ID {rec.id}."

    # ---------- Value parsing & Sanitizer ----------
    def _parse_values(self, text):
        res = {}
        if not text:
            return res
        for pair in [p.strip() for p in text.split(';') if p.strip()]:
            if '=' in pair:
                k, v = pair.split('=', 1)
                res[k.strip()] = v.strip()
        return res

    def _sanitize_command(self, data, values):
        if data.get('action') == 'create' and (data.get('model') or '').strip() == 'product.product':
            data['model'] = 'product.template'
        if 'lst_price' in values and 'list_price' not in values:
            values['list_price'] = values.pop('lst_price')
        if 'description' in values and 'description_sale' not in values:
            values['description_sale'] = values['description']
        return data, values

    # ---------- COMMAND executor ----------
    def _maybe_execute_command(self, assistant_text):
        blocks, text, start = [], (assistant_text or ''), 0
        while True:
            i = text.find("<<COMMAND>>", start)
            if i < 0: break
            j = text.find("<<END>>", i)
            if j < 0: break
            blocks.append(text[i+11:j].strip())
            start = j + 7

        results = []
        for b in blocks:
            lines = [ln.strip() for ln in b.splitlines() if ln.strip() and not ln.strip().startswith("#")]
            data = {}
            for ln in lines:
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    data[k.strip().lower()] = v.strip()
            action = data.get("action")
            model = data.get("model")
            values = self._parse_values(data.get("values",""))
            if data.get('lines'):
                values['lines'] = data['lines']

            data, values = self._sanitize_command(data, values)

            try:
                if action in ("create_sale_order","create_so"):
                    results.append(self._create_sale_order(values)); continue
                if action in ("add_sale_order_lines","add_so_lines"):
                    results.append(self._add_sale_order_lines(values)); continue
                if action in ("create_purchase_order","create_po"):
                    results.append(self._create_purchase_order(values)); continue
                if action in ("add_purchase_order_lines","add_po_lines"):
                    results.append(self._add_purchase_order_lines(values)); continue
                if action in ("create_product","new_product"):
                    results.append(self._create_product(values)); continue
                if action in ("create_partner","new_partner"):
                    results.append(self._create_partner(values)); continue

                if not action or not model:
                    results.append("Invalid COMMAND: missing action/model"); continue
                if model not in self._allowed_models():
                    results.append(f"Model '{model}' not allowed"); continue
                Model = self.env[model].sudo()

                if action == "create":
                    rec = Model.create(values)
                    results.append(f"Created {model} ID {rec.id}")
                elif action == "write":
                    rec_id = int(data.get("id") or "0")
                    if not rec_id: results.append("Write needs id"); continue
                    rec = Model.browse(rec_id)
                    if not rec.exists(): results.append(f"Record {rec_id} not found"); continue
                    rec.write(values)
                    results.append(f"Wrote {model} ID {rec_id}")
                elif action == "read":
                    dom = []
                    if data.get("search_name") and "name" in Model._fields:
                        dom = [("name","ilike", data.get("search_name"))]
                    recs = Model.search(dom, limit=10)
                    fields_list = ["name"] if "name" in Model._fields else list(Model._fields.keys())
                    vals = recs.read(fields_list)
                    results.append(f"Read {len(recs)} {model}: {vals}")
                else:
                    results.append(f"Unknown action '{action}'")
            except Exception as e:
                _logger.exception("Error executing COMMAND")
                results.append(f"Error: {e}")
        return results


class GrokAssistantMessage(models.Model):
    _name = "grok.assistant.message"
    _description = "Grok Assistant Message"
    _order = "create_date asc"

    session_id = fields.Many2one("grok.assistant.session", required=True, ondelete="cascade")
    role = fields.Selection([('system','System'),('user','User'),('assistant','Assistant')], required=True, default='user')
    content = fields.Text(required=True)
