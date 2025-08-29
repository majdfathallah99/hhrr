
import json
from datetime import date, datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError

def _dt(d):
    if isinstance(d, (date, datetime)):
        return fields.Date.to_string(d) if isinstance(d, date) and not isinstance(d, datetime) else fields.Datetime.to_string(d)
    return d

class AIBusinessTools(models.AbstractModel):
    _name = "ai.business.tools"
    _description = "Callable tools for the AI Assistant"


def tool_count_products(self, include_services=False):
    """
    Returns counts of products by type.
    include_services=False excludes service products from the main count.
    """
    env = self.env
    PT = env["product.template"].sudo()
    # Active only
    total_stock = PT.search_count([("active","=",True),("type","=","product")])
    total_consu = PT.search_count([("active","=",True),("type","=","consu")])
    counts = {
        "stockable": total_stock,
        "consumable": total_consu,
        "stockable_plus_consumable": total_stock + total_consu,
    }
    if include_services:
        total_service = PT.search_count([("active","=",True),("type","=","service")])
        counts["service"] = total_service
        counts["all_including_service"] = counts["stockable_plus_consumable"] + total_service
    return counts
    def tool_get_total_revenue(self, start_date, end_date, company_id=None, journal_types=None):
        env = self.env
        company = env.company if not company_id else env["res.company"].browse(company_id)
        aml = env["account.move.line"].sudo().with_company(company.id)
        domain = [
            ("parent_state", "=", "posted"),
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("company_id", "=", company.id),
            ("account_id.account_type", "=", "income"),

] + [
    {"type": "function", "function": {
        "name": "count_products",
        "description": "Count products by type (stockable, consumable, optionally services)",
        "parameters": {"type": "object","properties": {
            "include_services": {"type": "boolean", "default": False}
        }}
    }}
]
        if journal_types:
            domain.append(("move_id.journal_id.type", "in", journal_types))
        amount = sum(aml.search(domain).mapped("balance")) * -1.0
        return {"company": company.name, "start_date": _dt(start_date), "end_date": _dt(end_date), "revenue": amount}

    def tool_get_total_expense(self, start_date, end_date, company_id=None):
        env = self.env
        company = env.company if not company_id else env["res.company"].browse(company_id)
        aml = env["account.move.line"].sudo().with_company(company.id)
        domain = [
            ("parent_state", "=", "posted"),
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("company_id", "=", company.id),
            ("account_id.account_type", "=", "expense"),

] + [
    {"type": "function", "function": {
        "name": "count_products",
        "description": "Count products by type (stockable, consumable, optionally services)",
        "parameters": {"type": "object","properties": {
            "include_services": {"type": "boolean", "default": False}
        }}
    }}
]
        amount = sum(aml.search(domain).mapped("balance"))
        return {"company": company.name, "start_date": _dt(start_date), "end_date": _dt(end_date), "expense": amount}

    def tool_get_profit(self, start_date, end_date, company_id=None):
        rev = self.tool_get_total_revenue(start_date, end_date, company_id)
        exp = self.tool_get_total_expense(start_date, end_date, company_id)
        return {"company": rev["company"], "start_date": rev["start_date"], "end_date": rev["end_date"], "profit": rev["revenue"] - exp["expense"], "revenue": rev["revenue"], "expense": exp["expense"]}

    def tool_top_selling_products(self, start_date, end_date, company_id=None, limit=10):
        env = self.env
        company = env.company if not company_id else env["res.company"].browse(company_id)
        so_line = env["sale.order.line"].sudo().with_company(company.id)
        domain = [
            ("order_id.state", "in", ["sale", "done"]),
            ("order_id.date_order", ">=", start_date),
            ("order_id.date_order", "<=", end_date),
            ("company_id", "=", company.id),
            ("product_id.type", "in", ["product", "consu"]),

] + [
    {"type": "function", "function": {
        "name": "count_products",
        "description": "Count products by type (stockable, consumable, optionally services)",
        "parameters": {"type": "object","properties": {
            "include_services": {"type": "boolean", "default": False}
        }}
    }}
]
        lines = so_line.read_group(domain, ["product_id", "product_uom_qty:sum"], ["product_id"], limit=limit, orderby="product_uom_qty desc")
        res = [{"product_id": rec["product_id"][0], "product_name": rec["product_id"][1], "qty": rec["product_uom_qty"]} for rec in lines if rec.get("product_id")]
        return {"company": company.name, "items": res, "start_date": _dt(start_date), "end_date": _dt(end_date)}

    def tool_schemas(self):
        return [
            {"type": "function", "function": {
                "name": "get_profit",
                "description": "Get profit (revenue - expense) for a date range",
                "parameters": {"type": "object","properties": {
                    "start_date": {"type": "string"}, "end_date": {"type": "string"}, "company_id": {"type": "integer"}}, "required": ["start_date","end_date"]}
            }},
            {"type": "function", "function": {
                "name": "top_selling_products",
                "description": "Top selling products by quantity within a date range",
                "parameters": {"type": "object","properties": {
                    "start_date": {"type": "string"}, "end_date": {"type": "string"}, "limit": {"type": "integer","default":10}, "company_id": {"type": "integer"}}, "required": ["start_date","end_date"]}
            }},
            {"type": "function", "function": {
                "name": "get_total_revenue",
                "description": "Sum untaxed revenue using accounting Income accounts within a date range",
                "parameters": {"type": "object","properties": {
                    "start_date": {"type": "string"}, "end_date": {"type": "string"}, "company_id": {"type": "integer"}, "journal_types": {"type":"array","items":{"type":"string"}}}, "required": ["start_date","end_date"]}
            }},
            {"type": "function", "function": {
                "name": "get_total_expense",
                "description": "Sum expenses using accounting Expense accounts within a date range",
                "parameters": {"type": "object","properties": {
                    "start_date": {"type": "string"}, "end_date": {"type": "string"}, "company_id": {"type": "integer"}}, "required": ["start_date","end_date"]}
            }},

] + [
    {"type": "function", "function": {
        "name": "count_products",
        "description": "Count products by type (stockable, consumable, optionally services)",
        "parameters": {"type": "object","properties": {
            "include_services": {"type": "boolean", "default": False}
        }}
    }}
]

class AIResultMixin:
    def execute_tool(self, name, arguments):
        tools = {
            "get_profit": lambda args: self.env["ai.business.tools"].tool_get_profit(**args),
            "top_selling_products": lambda args: self.env["ai.business.tools"].tool_top_selling_products(**args),
            "get_total_revenue": lambda args: self.env["ai.business.tools"].tool_get_total_revenue(**args),
            "get_total_expense": lambda args: self.env["ai.business.tools"].tool_get_total_expense(**args),
        }
        if name not in tools:
            raise UserError(_("Unknown tool: %s") % name)
        return tools[name](arguments or {})
