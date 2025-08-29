
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
        ]
        lines = so_line.read_group(domain, ["product_id", "product_uom_qty:sum"], ["product_id"], limit=limit, orderby="product_uom_qty desc")
        res = [{"product_id": rec["product_id"][0], "product_name": rec["product_id"][1], "qty": rec["product_uom_qty"]} for rec in lines]
        return {"company": company.name, "items": res, "start_date": _dt(start_date), "end_date": _dt(end_date)}

    def tool_inventory_on_hand(self, product_id, location_id=None):
        env = self.env
        product = env["product.product"].browse(product_id)
        if not product.exists():
            raise UserError(_("Invalid product_id"))
        Quant = env["stock.quant"].sudo()
        qty = 0.0
        if location_id:
            location = env["stock.location"].browse(location_id)
            if not location.exists():
                raise UserError(_("Invalid location_id"))
            qty = Quant._get_available_quantity(product, location)
        else:
            quants = Quant.search([("product_id", "=", product.id), ("location_id.usage", "=", "internal")])
            qty = sum(quants.mapped("available_quantity"))
        return {"product_id": product.id, "product_name": product.display_name, "qty": qty}

    def tool_customer_balance(self, partner_id, company_id=None):
        env = self.env
        partner = env["res.partner"].browse(partner_id)
        company = env.company if not company_id else env["res.company"].browse(company_id)
        aml = env["account.move.line"].sudo().with_company(company.id)
        domain = [
            ("partner_id", "=", partner.id),
            ("account_id.internal_type", "=", "receivable"),
            ("parent_state", "=", "posted"),
            ("company_id", "=", company.id),
        ]
        balance = sum(aml.search(domain).mapped("balance"))
        return {"partner_id": partner.id, "partner_name": partner.display_name, "company": company.name, "balance": balance}

    def tool_schemas(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_profit",
                    "description": "Get profit (revenue - expense) for a date range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                            "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                            "company_id": {"type": "integer", "description": "Odoo company ID (optional)"}
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "top_selling_products",
                    "description": "Top selling products by quantity within a date range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                            "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                            "limit": {"type": "integer", "default": 10},
                            "company_id": {"type": "integer"}
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_total_revenue",
                    "description": "Sum untaxed revenue using accounting Income accounts within a date range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "company_id": {"type": "integer"},
                            "journal_types": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_total_expense",
                    "description": "Sum expenses using accounting Expense accounts within a date range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "company_id": {"type": "integer"}
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "inventory_on_hand",
                    "description": "On-hand quantity (not reserved) for a product in an optional location subtree",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer"},
                            "location_id": {"type": "integer"}
                        },
                        "required": ["product_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "customer_balance",
                    "description": "Account receivable balance for a customer in a company",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "partner_id": {"type": "integer"},
                            "company_id": {"type": "integer"}
                        },
                        "required": ["partner_id"]
                    }
                }
            }
        ]

class AIResultMixin:
    def execute_tool(self, name, arguments):
        tools = {
            "get_profit": lambda args: self.env["ai.business.tools"].tool_get_profit(**args),
            "top_selling_products": lambda args: self.env["ai.business.tools"].tool_top_selling_products(**args),
            "get_total_revenue": lambda args: self.env["ai.business.tools"].tool_get_total_revenue(**args),
            "get_total_expense": lambda args: self.env["ai.business.tools"].tool_get_total_expense(**args),
            "inventory_on_hand": lambda args: self.env["ai.business.tools"].tool_inventory_on_hand(**args),
            "customer_balance": lambda args: self.env["ai.business.tools"].tool_customer_balance(**args),
        }
        if name not in tools:
            raise UserError(_("Unknown tool: %s") % name)
        return tools[name](arguments or {})
