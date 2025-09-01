# -*- coding: utf-8 -*-
import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an Odoo assistant. "
    "When the user requests data changes or report queries, emit a COMMAND block:\n"
    "<<COMMAND>>\n"
    "action=<create|write|read>\n"
    "model=<odoo.model>\n"
    "values=<k=v;...>\n"
    "id=<record_id>\n"
    "search_name=<text>\n"
    "<<END>>\n"
    "Use normal text when no action is required."
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
            raise UserError(_("Please set API Key in /grok/config."))
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
            raise UserError(_("HTTP error calling provider: %s") % e)
        if resp.status_code >= 300:
            raise UserError(_("LLM API error: %s") % resp.text)
        data = resp.json()
        content = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
        return content or ''

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
