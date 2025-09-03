
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GptAssistantWizard(models.TransientModel):
    _name = "gpt.assistant.wizard"
    _description = "Ask GPT Assistant"

    thread_id = fields.Many2one('gpt.assistant.thread', string="Thread", required=True)
    prompt = fields.Text(required=True, string="Question / Instruction")

    def action_send(self):
        self.ensure_one()
        reply = self.thread_id.chat(self.prompt)
        # return to thread form with a notification
        action = self.env.ref('gpt5_odoo_assistant.action_gpt_assistant_threads').read()[0]
        action['res_id'] = self.thread_id.id
        action['view_mode'] = 'form'
        action['context'] = {'default_name': self.thread_id.name}
        return action
