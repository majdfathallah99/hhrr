# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class GrokConfig(models.TransientModel):
    _name = "grok.config.settings"
    _description = "Grok Assistant Settings"

    grok_api_key = fields.Char(string="x.ai API Key")
    grok_model = fields.Char(string="x.ai Model", default="grok-4-latest")
    grok_temperature = fields.Float(string="Temperature", default=0.0)
    grok_allowed_models = fields.Char(string="Allowed Models (comma separated)",
                                      default="res.partner,sale.order,sale.order.line,mrp.production,account.move")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        res.update({
            'grok_api_key': ICP.get_param('grok_odoo_assistant.api_key', ''),
            'grok_model': ICP.get_param('grok_odoo_assistant.model', 'grok-4-latest'),
            'grok_temperature': float(ICP.get_param('grok_odoo_assistant.temperature', '0.0') or 0.0),
            'grok_allowed_models': ICP.get_param('grok_odoo_assistant.allowed_models', 'res.partner,sale.order,sale.order.line'),
        })
        return res

    def action_save(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('grok_odoo_assistant.api_key', self.grok_api_key or '')
        ICP.set_param('grok_odoo_assistant.model', self.grok_model or 'grok-4-latest')
        ICP.set_param('grok_odoo_assistant.temperature', str(self.grok_temperature or 0.0))
        ICP.set_param('grok_odoo_assistant.allowed_models', self.grok_allowed_models or '')
        return {'type': 'ir.actions.act_window_close'}