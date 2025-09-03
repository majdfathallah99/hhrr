
# -*- coding: utf-8 -*-
import json, logging, requests
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
    message_ids = fields.One2many("gpt.assistant.message", "thread_id", copy=True)
    last_reply = fields.Text(readonly=True)
    temperature = fields.Float(default=0.2)
    system_prompt = fields.Text()

    sudo_mode = fields.Boolean(string="Sudo mode")
    allow_write = fields.Boolean(string="Allow write()")
    allow_create = fields.Boolean(string="Allow create()")
    allow_unlink = fields.Boolean(string="Allow unlink()")
    allow_execute_kw = fields.Boolean(string="Allow execute_kw")
    allow_all_models = fields.Boolean(string="Allow all models")
    allowed_model_ids = fields.Many2many("ir.model", string="Allowed models")

    tool_calls = fields.Integer(readonly=True)
    tokens_in = fields.Integer(readonly=True)
    tokens_out = fields.Integer(readonly=True)

    @api.constrains('sudo_mode','allow_all_models')
    def _check_super(self):
        for rec in self:
            if (rec.sudo_mode or rec.allow_all_models) and not self.env.user.has_group('gpt5_odoo_assistant.group_gpt_assistant_superuser'):
                raise ValidationError(_("Only GPT Assistant Superusers may enable Sudo/Allow all models."))

    def chat(self, prompt: str):
        self.ensure_one()
        if not prompt:
            raise UserError(_("Please provide a prompt."))
        cfg = self._get_settings()

        self.env['gpt.assistant.message'].create({'thread_id': self.id, 'role': 'user', 'content': prompt})

        messages = []
        system_prompt = self.system_prompt or self._default_system_prompt()
        messages.append({'role': 'system', 'content': system_prompt})
        for m in self.message_ids.sorted('id'):
            messages.append({'role': m.role, 'content': m.content if m.role != 'tool' else (m.tool_response or '')})
        messages.append({'role': 'user', 'content': prompt})

        tools = self._tool_schemas()
        reply_text, tool_iters, t_in, t_out = self._call_model_with_tools(cfg, messages, tools, temperature=self.temperature)

        self.write({'last_reply': reply_text, 'tool_calls': self.tool_calls + tool_iters, 'tokens_in': (self.tokens_in or 0) + (t_in or 0), 'tokens_out': (self.tokens_out or 0) + (t_out or 0)})
        self.env['gpt.assistant.message'].create({'thread_id': self.id, 'role': 'assistant', 'content': reply_text})
        return {'reply': reply_text}

    def _call_model_with_tools(self, cfg, messages, tools, temperature=0.2):
        base = cfg['base_url'].rstrip('/')
        model = cfg['model']
        headers = {'Authorization': f"Bearer {cfg['api_key']}", 'Content-Type':'application/json'}
        url = f"{base}/chat/completions"
        payload = {'model': model, 'messages': messages, 'tools': tools, 'tool_choice':'auto', 'temperature': temperature}

        tokens_in=tokens_out=0
        iters=0
        max_iters=4
        while True:
            resp = requests.post(url, headers=headers, data=_json_dumps(payload), timeout=120)
            if resp.status_code >= 300:
                raise UserError(_("OpenAI API error: %s") % resp.text)
            data = resp.json()
            choice = (data.get('choices') or [{}])[0]
            message = choice.get('message', {})
            usage = data.get('usage') or {}
            tokens_in += usage.get('prompt_tokens',0); tokens_out += usage.get('completion_tokens',0)
            if message.get('tool_calls'):
                if iters >= max_iters:
                    messages.append({'role':'assistant','content':'Tool call limit reached.'})
                    break
                for call in message['tool_calls']:
                    name = call.get('function',{}).get('name')
                    arg_str = call.get('function',{}).get('arguments') or '{}'
                    try:
                        args = json.loads(arg_str) if isinstance(arg_str,str) else (arg_str or {})
                    except Exception:
                        args = {}
                    tool_result = self._execute_tool(name, args)
                    self.env['gpt.assistant.message'].create({
                        'thread_id': self.id, 'role':'tool', 'tool_name': name,
                        'tool_args': _json_dumps(args), 'tool_response': _json_dumps(tool_result)[:65535],
                    })
                    messages.append({'role':'tool','content':_json_dumps(tool_result),'tool_call_id':call.get('id')})
                    iters += 1
                payload['messages'] = messages
                continue
            else:
                return message.get('content') or '', iters, tokens_in, tokens_out

    def _tool_schemas(self):
        return [
            {'type':'function','function':{
                'name':'search_read',
                'description':'Search and read records from an Odoo model.',
                'parameters':{'type':'object','properties':{
                    'model':{'type':'string'},
                    'domain':{'type':'array'},
                    'fields':{'type':'array','items':{'type':'string'}},
                    'limit':{'type':'integer'}
                },'required':['model']}
            }},
            {'type':'function','function':{
                'name':'get_model_fields',
                'description':'List fields for a model.',
                'parameters':{'type':'object','properties':{'model':{'type':'string'}},'required':['model']}
            }},
            {'type':'function','function':{
                'name':'create',
                'description':'Create a record (if allowed).',
                'parameters':{'type':'object','properties':{
                    'model':{'type':'string'},'vals':{'type':'object'}
                },'required':['model','vals']}
            }},
            {'type':'function','function':{
                'name':'write',
                'description':'Write records (if allowed).',
                'parameters':{'type':'object','properties':{
                    'model':{'type':'string'},'ids':{'type':'array','items':{'type':'integer'}},'vals':{'type':'object'}
                },'required':['model','ids','vals']}
            }},
            {'type':'function','function':{
                'name':'unlink',
                'description':'Delete records (if allowed).',
                'parameters':{'type':'object','properties':{
                    'model':{'type':'string'},'ids':{'type':'array','items':{'type':'integer'}}
                },'required':['model','ids']}
            }},
            {'type':'function','function':{
                'name':'run_server_action',
                'description':'Run a server action by xml_id or id (if allowed).',
                'parameters':{'type':'object','properties':{
                    'xml_id':{'type':'string'},'action_id':{'type':'integer'},'context':{'type':'object'}
                }}
            }},
        ]

    def _model_ok(self, model_name):
        if self.allow_all_models:
            return True
        if not self.allowed_model_ids:
            return False
        return any(m.model == model_name for m in self.allowed_model_ids)

    def _env_for_tools(self):
        return self.env.sudo() if (self.sudo_mode and self.env.user.has_group('gpt5_odoo_assistant.group_gpt_assistant_superuser')) else self.env

    def _execute_tool(self, name, args):
        env = self._env_for_tools()
        name = (name or '').strip()
        res = {'ok': True, 'tool': name}

        def ensure_model(model):
            if not model:
                raise UserError(_('Missing model.'))
            if not self._model_ok(model):
                raise AccessError(_('Model not allowed in this thread.'))
            if model not in env:
                raise UserError(_('Unknown model: %s') % model)

        try:
            if name == 'search_read':
                model = args.get('model'); ensure_model(model)
                domain = args.get('domain') or []; 
                if isinstance(domain, str):
                    domain = safe_eval(domain, {})
                fields = args.get('fields') or []; limit = int(args.get('limit') or 80)
                recs = env[model].search(domain, limit=limit)
                res['data'] = recs.read(fields or ['id','name']); return res

            if name == 'get_model_fields':
                model = args.get('model'); ensure_model(model)
                fields_meta = []
                for f_name, f in env[model]._fields.items():
                    fields_meta.append({'name':f_name,'type':f.type,'string':f.string,'help':f.help or '','readonly':f.readonly,'required':f.required})
                res['fields'] = fields_meta; return res

            if name == 'create':
                if not self.allow_create: raise AccessError(_('Create not allowed.'))
                model = args.get('model'); ensure_model(model)
                vals = args.get('vals') or {}
                rec = env[model].create(vals); res['id'] = rec.id; return res

            if name == 'write':
                if not self.allow_write: raise AccessError(_('Write not allowed.'))
                model = args.get('model'); ensure_model(model)
                ids = args.get('ids') or []; vals = args.get('vals') or {}
                env[model].browse(ids).write(vals); res['ids'] = ids; return res

            if name == 'unlink':
                if not self.allow_unlink: raise AccessError(_('Unlink not allowed.'))
                model = args.get('model'); ensure_model(model)
                ids = args.get('ids') or []; env[model].browse(ids).unlink(); res['ids'] = ids; return res

            if name == 'run_server_action':
                if not self.allow_execute_kw: raise AccessError(_('Execute not allowed.'))
                xml_id = args.get('xml_id'); action_id = args.get('action_id'); ctx = args.get('context') or {}
                if xml_id:
                    act = env.ref(xml_id)
                elif action_id:
                    act = env['ir.actions.server'].browse(int(action_id))
                else:
                    raise UserError(_('Provide xml_id or action_id'))
                act.with_context(**ctx).run(); res['done'] = True; return res

            raise UserError(_('Unknown tool: %s') % name)
        except Exception as e:
            _logger.exception('Tool execution error')
            return {'ok': False, 'tool': name, 'error': str(e)}

    def _get_settings(self):
        ICP = self.env['ir.config_parameter'].sudo()
        base_url = ICP.get_param('gpt5.base_url', default='https://api.openai.com/v1')
        api_key = ICP.get_param('gpt5.api_key') or ''
        model = ICP.get_param('gpt5.model', default='gpt-5')
        if not api_key:
            raise UserError(_('Set the API key in Settings > General Settings > GPT-5 Assistant.'))
        return {'base_url': base_url, 'api_key': api_key, 'model': model}

    def _default_system_prompt(self):
        return ('You are an AI assistant embedded in Odoo. '
                'Use tools for factual ERP answers. '
                'Be concise and safe.')

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
