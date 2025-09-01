# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class GrokAssistantSession(models.Model):
    _name = "grok.assistant.session"
    _description = "Grok Assistant Session"

    name = fields.Char(default="جلسة محادثة")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    execute = fields.Boolean(string="تنفيذ الإجراءات", default=False)
    message_ids = fields.One2many("grok.assistant.message", "session_id", string="Messages")

    # Lightweight rule-based replies (Arabic)
    def _smart_reply(self, text):
        t = (text or "").strip()
        if not t:
            return _("اكتب رسالتك ثم اضغط إرسال.")
        # Common intents
        s = t.replace("؟","").replace("?","").strip()
        if s in ("ماذا","شنو","what","??","?"):
            return _("تمام. ممكن توضح طلبك بكلمة أو كلمتين؟ مثل: «أنشئ منتج اسمه كيبورد» أو «اعرض طلبات البيع اليوم».")
        if "كم عمري" in s:
            return _("لا أعرف عمرك لأنني لا أملك معلوماتك الشخصية. أعطني تاريخ ميلادك (يوم/شهر/سنة) وسأحسبه لك فورًا.")
        # Create product intent (e.g., "اريد منتج", "اريد منتج كيبورد")
        if s.startswith("اريد منتج"):
            name = s.replace("اريد منتج", "", 1).strip()
            if not name:
                name = _("منتج جديد")
            cmd = "<<COMMAND>> action=create model=product.template values=name={}&type=product&sale_ok=True&purchase_ok=True <<END>>".format(name)
            return cmd
        return _("حاضر. صف لي ما تريد: إنشاء (منتج/فاتورة/عميل) أو البحث (عن عميل/منتج) أو تعديل سجل.")

    # EXECUTOR: parse minimal COMMAND block and execute if allowed
    def _parse_command(self, content):
        if not content or "<<COMMAND>>" not in content or "<<END>>" not in content:
            return None
        chunk = content.split("<<COMMAND>>",1)[1].split("<<END>>",1)[0].strip()
        # Very simple key=value parser separated by spaces
        parts = [p for p in chunk.split() if "=" in p]
        data = {}
        for p in parts:
            k,v = p.split("=",1)
            data[k.strip()] = v.strip()
        # Normalize
        data["action"] = data.get("action","").strip()
        data["model"]  = data.get("model","").strip()
        return data

    def _parse_values(self, chunk):
        """Extract values=... into dict (k1=v1&k2=v2)."""
        vals = {}
        if "values=" not in chunk:
            return vals
        raw = chunk.split("values=",1)[1]
        # cut after first space token (end of values)
        for sep in [" id="," model="," action="," lines="]:
            if sep in raw:
                raw = raw.split(sep,1)[0]
        raw = raw.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        pairs = [x for x in raw.split("&") if "=" in x]
        for pair in pairs:
            k,v = pair.split("=",1)
            vals[k.strip()] = v.strip()
        return vals

    def _maybe_execute_command(self, content):
        self.ensure_one()
        if not self.execute:
            return []
        data = self._parse_command(content) or {}
        if not data:
            return []
        action = data.get("action")
        model = data.get("model")
        vals = self._parse_values(content)
        # Sanitize: product.product -> product.template, alias fields
        if action == "create" and model == "product.product":
            model = "product.template"
        if "lst_price" in vals and "list_price" not in vals:
            vals["list_price"] = vals.pop("lst_price")
        if "description" in vals and "description_sale" not in vals:
            vals["description_sale"] = vals["description"]
        # Execute limited safe actions
        allowed_models = ["product.template","res.partner","sale.order","purchase.order"]
        if action == "create" and model in allowed_models:
            rec = self.env[model].sudo().create(vals or {"name": _("عنصر جديد")})
            return [ _("تم إنشاء سجل في {}: #{}").format(model, rec.id) ]
        return []

class GrokAssistantMessage(models.Model):
    _name = "grok.assistant.message"
    _description = "Grok Assistant Message"
    _order = "id desc"

    session_id = fields.Many2one("grok.assistant.session", required=True, ondelete="cascade")
    role = fields.Selection([("user","User"),("assistant","Assistant")], default="user", required=True)
    content = fields.Text()

    @api.model
    def send_user_message(self, session, text):
        # store user message
        self.create({"session_id": session.id, "role":"user", "content": text or ""})
        # produce assistant reply (rule-based to avoid external deps)
        reply = session._smart_reply(text or "")
        self.create({"session_id": session.id, "role":"assistant", "content": reply})
        # execute if needed
        results = session._maybe_execute_command(reply)
        return reply, results
