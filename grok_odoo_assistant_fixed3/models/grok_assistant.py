# -*- coding: utf-8 -*-
import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

XAI_ENDPOINT = "https://api.x.ai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are an Odoo assistant. "
    "When the user asks for data changes or report queries, "
    "output a COMMAND block using this exact format when appropriate:\n"
    "<<COMMAND>>\n"
    "action=<create|write|read>\n"
    "model=<odoo.model>\n"
    "# For create: values as key=value;key=value\n"
    "values=<k=v;...>\n"
    "# For write: id is required\n"
    "id=<record_id>\n"
    "# For read: optional search_name for name ilike\n"
    "search_name=<text>\n"
    "<<END>>\n"
    "Otherwise, just answer normally."
)

class GrokAssistantSession(models.Model):
    _name = "grok.assistant.session"
    _description = "Grok Assistant Session"
    _order = "create_date desc"

    name = fields.Char(default=lambda self: _("Session"))
    message_ids = fields.One2many("grok.assistant.message", "session_id", string="Messages")
    active = fields.Boolean(default=True)

    def _allowed_models(self):
        params = self.env['ir.config_parameter'].sudo()
        raw = params.get_param('grok_odoo_assistant.allowed_models', '') or ''
        names = [n.strip() for n in raw.split(',') if n.strip()]
        existing = [n for n in names if n in self.env]
        return existing

    def _call_xai(self, user_text):
        params = self.env['ir.config_parameter'].sudo()
        api_key = params.get_param('grok_odoo_assistant.api_key') or ''
        if not api_key:
            raise UserError(_("Please set x.ai API Key in Grok Settings."))

        model = params.get_param('grok_odoo_assistant.model', 'grok-4-latest') or 'grok-4-latest'
        try:
            temp = float(params.get_param('grok_odoo_assistant.temperature', '0.0') or 0.0)
        except Exception:
            temp = 0.0

        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        last_msgs = self.message_ids.sorted(key=lambda m: m.create_date)[-10:]
        for m in last_msgs:
            messages.append({'role': m.role, 'content': m.content})
        messages.append({'role': 'user', 'content': user_text})

        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {'messages': messages, 'model': model, 'stream': False, 'temperature': temp}
        resp = requests.post(XAI_ENDPOINT, headers=headers, json=payload, timeout=60)
        if resp.status_code >= 300:
            raise UserError(_("x.ai API error: %s") % resp.text)
        data = resp.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        return content

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
            action = data.get("action"); model = data.get("model")
            if not action or not model:
                results.append("Invalid COMMAND: missing action/model"); continue
            if model not in self._allowed_models():
                results.append(f"Model '{model}' not allowed"); continue
            Model = self.env[model].sudo()
            try:
                if action == "create":
                    values = {}
                    for pair in (data.get("values") or "").split(";"):
                        if pair.strip() and "=" in pair:
                            k, v = pair.split("=", 1)
                            values[k.strip()] = v.strip()
                    rec = Model.create(values)
                    results.append(f"Created {model} ID {rec.id}")
                elif action == "write":
                    rec_id = int(data.get("id") or "0")
                    if not rec_id: results.append("Write needs id"); continue
                    values = {}
                    for pair in (data.get("values") or "").split(";"):
                        if pair.strip() and "=" in pair:
                            k, v = pair.split("=", 1)
                            values[k.strip()] = v.strip()
                    rec = Model.browse(rec_id)
                    if not rec.exists(): results.append(f"Record {rec_id} not found"); continue
                    rec.write(values)
                    results.append(f"Wrote {model} ID {rec_id}")
                elif action == "read":
                    search_name = data.get("search_name") or ""
                    domain = [("name", "ilike", search_name)] if (search_name and "name" in Model._fields) else []
                    recs = Model.search(domain, limit=10)
                    fields_list = ["name"] if "name" in Model._fields else list(Model._fields.keys())
                    vals = recs.read(fields_list)
                    results.append(f"Read {len(recs)} {model}: {vals}")
                else:
                    results.append(f"Unknown action '{action}'")
            except Exception as e:
                _logger.exception("Error executing command from Grok")
                results.append(f"Error: {e}")
        return results


class GrokAssistantMessage(models.Model):
    _name = "grok.assistant.message"
    _description = "Grok Assistant Message"
    _order = "create_date asc"

    session_id = fields.Many2one("grok.assistant.session", required=True, ondelete="cascade")
    role = fields.Selection([('system','System'),('user','User'),('assistant','Assistant')], required=True, default='user')
    content = fields.Text(required=True)