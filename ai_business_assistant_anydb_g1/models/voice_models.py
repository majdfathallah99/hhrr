from odoo import models, fields, api

class AIVoiceRoom(models.Model):
    _name = "ai.voice.room"
    _description = "AI Live Voice Chat Room"
    _rec_name = "name"

    name = fields.Char(required=True)
    room_key = fields.Char(required=True, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('ai.voice.room') or 'room')
    active = fields.Boolean(default=True)
    participant_ids = fields.Many2many('res.users', string='Participants')
    linked_model = fields.Char(help="Optional: technical model name to link this room to a record")
    linked_res_id = fields.Integer(help="Optional: linked record ID")
    notes = fields.Text()

class IrSequence(models.Model):
    _inherit = "ir.sequence"
