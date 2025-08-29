
from odoo import api, fields, models

class AIAssistantLog(models.Model):
    _name = "ai.assistant.log"
    _description = "AI Assistant Log"
    _order = "create_date desc"

    name = fields.Char(string="Question", required=True)
    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    response_text = fields.Text()
    tool_calls_json = fields.Text(string="Tool Calls (JSON)")
    tool_results_json = fields.Text(string="Tool Results (JSON)")
