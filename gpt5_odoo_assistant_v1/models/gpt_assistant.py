
# -*- coding: utf-8 -*-
import json
import logging
import time
from typing import Any, Dict, List

import requests

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


def _json_dumps(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'), default=str)


class GptAssistantThread(models.Model):
    _name = "gpt.assistant.thread"
    _description = "GPT Assistant Thread"
    _order = "id desc"

    name = fields.Char(default=lambda self: _("Assistant Thread"))
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True, readonly=True)
    state = fields.Selection([('draft','Draft'), ('active','Active'), ('archived','Archived')], default='active')
    message_ids = fields.One2many("gpt.assistant.message", "thread_id", string="Messages", copy=True)
    last_reply = fields.Text(readonly=True)
    temperature = fields.Float(default=0.2)
    system_prompt = fields.Text(help="Optional system prompt prepended to the conversation. Leave blank to use default.")
    # Safety gates
    sudo_mode = fields.Boolean(string="Sudo mode (read all records)", help="If on and user has Superuser group, tool calls are executed with sudo().")
    allow_write = fields.Boolean(string="Allow write()")
    allow_create = fields.Boolean(string="Allow create()")
    allow_unlink = fields.Boolean(string="Allow unlink()")
    allow_execute_kw = fields.Boolean(string="Allow execute_kw (advanced)")
    allow_all_models = fields.Boolean(string="Allow all models (dangerous)", help="Expose all models to tools. Requires Superuser group.")
    allowed_model_ids = fields.Many2many("ir.model", string="Allowed models")
    # Stats
    tool_calls = fields.Integer(readonly=True)
    tokens_in = fields.Integer(readonly=True)
    tokens_out = fields.Integer(readonly=True)

    @api.constrains('sudo_mode', 'allow_all_models')
    def _check_super_powers(self):
        for rec in self:
            if (rec.sudo_mode or rec.allow_all_models) and not self.env.user.has_group('gpt5_odoo_assistant.group_gpt_assistant_superuser'):
                raise ValidationError(_("Only GPT Assistant Superusers may enable Sudo mode or Allow all models."))

    # -----------------------------
    # Public API
    # -----------------------------
    def chat(self, prompt: str) -> Dict[str, Any]:
        self.ensure_one()
        if not prompt:
            raise UserError(_("Please provide a prompt."))

        cfg = self._get_settings()
        # persist user message
        user_msg = self.env['gpt.assistant.message'].create({
            'thread_id': self.id,
            'role': 'user',
            'content': prompt,
        })

        # Assemble messages
        messages = []
        system_prompt = self.system_prompt or self._default_system_prompt()
        messages.append({'role': 'system', 'content': system_prompt})
        for m in self.message_ids.sorted('id'):
            messages.append({'role': m.role, 'content': m.content if m.role != 'tool' else (m.tool_response or '')})
        messages.append({'role': 'user', 'content': prompt})

        # Compose tools schema
        tools = self._tool_schemas()

        # Call model (Responses API preferred; fallback to Chat Completions)
        reply_text, tool_iters, tokens_in, tokens_out = self._call_model_with_tools(cfg, messages, tools, temperature=self.temperature)

        # Save assistant reply
        self.write({
            'last_reply': reply_text,
            'tool_calls': self.tool_calls + tool_iters,
            'tokens_in': (self.tokens_in or 0) + (tokens_in or 0),
            'tokens_out': (self.tokens_out or 0) + (tokens_out or 0),
        })
        self.env['gpt.assistant.message'].create({
            'thread_id': self.id,
            'role': 'assistant',
            'content': reply_text,
        })
        return {'reply': reply_text}

    # -----------------------------
    # OpenAI call orchestration
    # -----------------------------
    def _call_model_with_tools(self, cfg, messages, tools, temperature=0.2):
        """Loop to satisfy tool calls until a final answer is produced."""
        # Try Responses API
        base = cfg['base_url'].rstrip('/')
        model = cfg['model']
        headers = {
            'Authorization': f"Bearer {cfg['api_key']}",
            'Content-Type': 'application/json',
        }

        # We'll first try Chat Completions style tool calling since it's stable across versions.
        url = f"{base}/chat/completions"
        payload = {
            'model': model,
            'messages': messages,
            'tools': tools,
            'tool_choice': 'auto',
            'temperature': temperature,
        }

        tokens_in = tokens_out = 0
        max_iters = 4
        tool_iters = 0

        while True:
            resp = requests.post(url, headers=headers, data=_json_dumps(payload), timeout=120)
            if resp.status_code >= 300:
                # Try Responses API fallback once
                _logger.warning("Chat Completions failed (%s). Trying Responses API fallback.", resp.text[:300])
                url2 = f"{base}/responses"
                payload2 = {
                    'model': model,
                    'input': messages,
                    'temperature': temperature,
                    'tools': tools,
                    'tool_choice': 'auto',
                }
                resp2 = requests.post(url2, headers=headers, data=_json_dumps(payload2), timeout=120)
                if resp2.status_code >= 300:
                    raise UserError(_("OpenAI API error: %s") % (resp2.text,))
                data2 = resp2.json()
                # Attempt to read the top-level output text (Responses API schema)
                reply_text = self._extract_responses_api_text(data2)
                return reply_text, tool_iters, tokens_in, tokens_out

            data = resp.json()
            choice = (data.get('choices') or [{}])[0]
            message = choice.get('message', {})
            usage = data.get('usage') or {}
            tokens_in += usage.get('prompt_tokens', 0)
            tokens_out += usage.get('completion_tokens', 0)

            if message.get('tool_calls'):
                if tool_iters >= max_iters:
                    # Prevent infinite loops
                    messages.append({'role': 'assistant', 'content': 'Tool call limit reached. Stopping.'})
                    break
                for call in message['tool_calls']:
                    name = call.get('function', {}).get('name')
                    arg_str = call.get('function', {}).get('arguments') or '{}'
                    try:
                        args = json.loads(arg_str) if isinstance(arg_str, str) else (arg_str or {})
                    except Exception:
                        args = {}
                    tool_result = self._execute_tool(name, args)
                    # record a tool message
                    self.env['gpt.assistant.message'].create({
                        'thread_id': self.id,
                        'role': 'tool',
                        'tool_name': name,
                        'tool_args': _json_dumps(args),
                        'tool_response': _json_dumps(tool_result)[:65535],
                    })
                    # add to messages for the next round
                    messages.append({'role': 'tool', 'content': _json_dumps(tool_result), 'tool_call_id': call.get('id')})
                    tool_iters += 1
                # continue loop to get final answer
                payload['messages'] = messages
                continue
            else:
                reply_text = message.get('content') or ''
                return reply_text, tool_iters, tokens_in, tokens_out

    def _extract_responses_api_text(self, data: Dict[str, Any]) -> str:
        # Best-effort extract for Responses API; shape may vary over time
        try:
            # Some variants have data['output'][0]['content'][0]['text']
            out = data.get('output') or data.get('choices') or []
            if out and isinstance(out, list):
                first = out[0]
                content = first.get('content') if isinstance(first, dict) else None
                if isinstance(content, list) and content:
                    txt = content[0].get('text')
                    if txt:
                        return txt
            # Fallback
            return json.dumps(data)[:4000]
        except Exception:
            return json.dumps(data)[:4000]

    # -----------------------------
    # Tool schemas & execution
    # -----------------------------
    def _tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            { 'type': 'function', 'function': {
                'name': 'search_read',
                'description': 'Search and read records from an Odoo model. Use when you need data. Domain uses Odoo domain syntax.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'model': {'type': 'string'},
                        'domain': {'type': 'array', 'description': 'Odoo domain, e.g. [["name","ilike","Acme"]]'},
                        'fields': {'type': 'array', 'items': {'type':'string'}},
                        'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500}
                    },
                    'required': ['model']
                }
            }},
            { 'type': 'function', 'function': {
                'name': 'get_model_fields',
                'description': 'List fields for a given model with types and help.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'model': {'type': 'string'}
                    },
                    'required': ['model']
                }
            }},
            { 'type': 'function', 'function': {
                'name': 'create',
                'description': 'Create a record in a model. Only allowed if allow_create is True.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'model': {'type': 'string'},
                        'vals': {'type': 'object'}
                    },
                    'required': ['model', 'vals']
                }
            }},
            { 'type': 'function', 'function': {
                'name': 'write',
                'description': 'Write to records. Only allowed if allow_write is True.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'model': {'type': 'string'},
                        'ids': {'type': 'array', 'items': {'type':'integer'}},
                        'vals': {'type': 'object'}
                    },
                    'required': ['model', 'ids', 'vals']
                }
            }},
            { 'type': 'function', 'function': {
                'name': 'unlink',
                'description': 'Delete records. Only allowed if allow_unlink is True. USE WITH CARE.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'model': {'type': 'string'},
                        'ids': {'type': 'array', 'items': {'type':'integer'}}
                    },
                    'required': ['model', 'ids']
                }
            }},
            { 'type': 'function', 'function': {
                'name': 'run_server_action',
                'description': 'Run a server action by XML ID or ID with context. Only if allow_execute_kw is True.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'xml_id': {'type': 'string'},
                        'action_id': {'type': 'integer'},
                        'context': {'type': 'object'}
                    }
                }
            }},
        ]

    def _model_ok(self, model_name: str) -> bool:
        self.ensure_one()
        if self.allow_all_models:
            return True
        if not self.allowed_model_ids:
            return False
        return any(m.model == model_name for m in self.allowed_model_ids)

    def _env_for_tools(self):
        return self.env.sudo() if (self.sudo_mode and self.env.user.has_group('gpt5_odoo_assistant.group_gpt_assistant_superuser')) else self.env

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        env = self._env_for_tools()
        name = (name or '').strip()
        res: Dict[str, Any] = {'ok': True, 'tool': name}

        def ensure_model(model):
            if not model:
                raise UserError(_('Missing model.'))
            if not self._model_ok(model):
                raise AccessError(_('Model not allowed in this thread.'))
            if model not in env:
                raise UserError(_('Unknown model: %s') % model)

        try:
            if name == 'search_read':
                model = args.get('model')
                ensure_model(model)
                domain = args.get('domain') or []
                if isinstance(domain, str):
                    domain = safe_eval(domain, {})
                fields = args.get('fields') or []
                limit = int(args.get('limit') or 80)
                records = env[model].search(domain, limit=limit)
                data = records.read(fields or ['id','name'])
                res['data'] = data
                return res

            if name == 'get_model_fields':
                model = args.get('model')
                ensure_model(model)
                fields_meta = []
                for f_name, f in env[model]._fields.items():
                    fields_meta.append({
                        'name': f_name,
                        'type': f.type,
                        'string': f.string,
                        'help': f.help or '',
                        'readonly': f.readonly,
                        'required': f.required,
                    })
                res['fields'] = fields_meta
                return res

            if name == 'create':
                if not self.allow_create:
                    raise AccessError(_('Create not allowed for this thread.'))
                model = args.get('model')
                ensure_model(model)
                vals = args.get('vals') or {}
                rec = env[model].create(vals)
                res['id'] = rec.id
                return res

            if name == 'write':
                if not self.allow_write:
                    raise AccessError(_('Write not allowed for this thread.'))
                model = args.get('model')
                ensure_model(model)
                ids = args.get('ids') or []
                vals = args.get('vals') or {}
                env[model].browse(ids).write(vals)
                res['ids'] = ids
                return res

            if name == 'unlink':
                if not self.allow_unlink:
                    raise AccessError(_('Unlink not allowed for this thread.'))
                model = args.get('model')
                ensure_model(model)
                ids = args.get('ids') or []
                env[model].browse(ids).unlink()
                res['ids'] = ids
                return res

            if name == 'run_server_action':
                if not self.allow_execute_kw:
                    raise AccessError(_('Execute not allowed for this thread.'))
                xml_id = args.get('xml_id')
                action_id = args.get('action_id')
                ctx = args.get('context') or {}
                if xml_id:
                    act = env.ref(xml_id)
                elif action_id:
                    act = env['ir.actions.server'].browse(int(action_id))
                else:
                    raise UserError(_('Provide xml_id or action_id'))
                act.with_context(**ctx).run()
                res['done'] = True
                return res

            raise UserError(_('Unknown tool: %s') % name)
        except Exception as e:
            _logger.exception('Tool execution error')
            return {'ok': False, 'tool': name, 'error': str(e)}

    def _get_settings(self) -> Dict[str, str]:
        ICP = self.env['ir.config_parameter'].sudo()
        base_url = ICP.get_param('gpt5.base_url', default='https://api.openai.com/v1')
        api_key = ICP.get_param('gpt5.api_key') or ''
        model = ICP.get_param('gpt5.model', default='gpt-5')
        if not api_key:
            raise UserError(_('Set the API key in Settings > General Settings > GPT-5 Assistant.'))
        return {'base_url': base_url, 'api_key': api_key, 'model': model}

    def _default_system_prompt(self) -> str:
        return (
            'You are an AI assistant embedded in Odoo. '
            'You can call tools to query or modify Odoo data. '
            'Prefer using tools for any factual answers from the ERP. '
            'Be concise. If you need fields list or IDs, call get_model_fields or search_read. '
            'Always propose the minimal safe change when writing.'
        )


class GptAssistantMessage(models.Model):
    _name = "gpt.assistant.message"
    _description = "GPT Assistant Message"
    _order = "id asc"

    thread_id = fields.Many2one("gpt.assistant.thread", required=True, ondelete='cascade')
    role = fields.Selection([('system','system'), ('user','user'), ('assistant','assistant'), ('tool','tool')], required=True)
    content = fields.Text()
    tool_name = fields.Char()
    tool_args = fields.Text()
    tool_response = fields.Text()
    tokens = fields.Integer()


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gpt5_base_url = fields.Char(string='API Base URL', config_parameter='gpt5.base_url', default='https://api.openai.com/v1')
    gpt5_model = fields.Char(string='Model', config_parameter='gpt5.model', default='gpt-5')
    gpt5_api_key = fields.Char(string='API Key', config_parameter='gpt5.api_key')
