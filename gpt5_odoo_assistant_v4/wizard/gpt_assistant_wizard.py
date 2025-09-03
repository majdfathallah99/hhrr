
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class GptAssistantWizard(models.TransientModel):
    _name = "gpt.assistant.wizard"
    _description = "Ask GPT Assistant"

    thread_id = fields.Many2one('gpt.assistant.thread', required=True)
    prompt = fields.Text(required=True, string="Question / Instruction")

    def action_send(self):
        self.ensure_one()
        reply = self.thread_id.chat(self.prompt)
        action = self.env.ref('gpt5_odoo_assistant.action_gpt_assistant_threads').read()[0]
        action['res_id'] = self.thread_id.id
        action['view_mode'] = 'form'
        return action
