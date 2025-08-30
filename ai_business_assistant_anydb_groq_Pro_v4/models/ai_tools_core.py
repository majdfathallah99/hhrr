
import json
from datetime import date, datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

def _dt_str(d):
    if isinstance(d, datetime):
        return fields.Datetime.to_string(d)
    if isinstance(d, date):
        return fields.Date.to_string(d)
    return d

class AIBusinessToolsCore(models.AbstractModel):
    _name = "ai.business.tools.core"
    _description = "AI Business Tools (Core + Generic)"

    # ---------- Helpers ----------
    def _env_for_tools(self):
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("ai_business_assistant.ai_superuser_mode") == "True":
            return self.env.sudo()
        return self.env

    # ---------- Business tools (examples) ----------
    def tool_get_total_revenue(self, start_date, end_date, company_id=None, journal_types=None):
        env = self._env_for_tools()
        company = env.company if not company_id else env["res.company"].browse(company_id)
        aml = env["account.move.line"].with_company(company.id)
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
        return {"company": company.name, "start_date": _dt_str(start_date), "end_date": _dt_str(end_date), "revenue": amount}

    def tool_get_total_expense(self, start_date, end_date, company_id=None):
        env = self._env_for_tools()
        company = env.company if not company_id else env["res.company"].browse(company_id)
        aml = env["account.move.line"].with_company(company.id)
        domain = [
            ("parent_state", "=", "posted"),
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("company_id", "=", company.id),
            ("account_id.account_type", "=", "expense"),
        ]
        amount = sum(aml.search(domain).mapped("balance"))
        return {"company": company.name, "start_date": _dt_str(start_date), "end_date": _dt_str(end_date), "expense": amount}

    def tool_get_profit(self, start_date, end_date, company_id=None):
        rev = self.tool_get_total_revenue(start_date, end_date, company_id)
        exp = self.tool_get_total_expense(start_date, end_date, company_id)
        return {
            "company": rev["company"],
            "start_date": rev["start_date"],
            "end_date": rev["end_date"],
            "revenue": rev["revenue"],
            "expense": exp["expense"],
            "profit": rev["revenue"] - exp["expense"],
        }

    def tool_top_selling_products(self, start_date, end_date, company_id=None, limit=10):
        env = self._env_for_tools()
        company = env.company if not company_id else env["res.company"].browse(company_id)
        so_line = env["sale.order.line"].with_company(company.id)
        domain = [
            ("order_id.state", "in", ["sale", "done"]),
            ("order_id.date_order", ">=", start_date),
            ("order_id.date_order", "<=", end_date),
            ("company_id", "=", company.id),
            ("product_id.type", "in", ["product", "consu"]),
        ]
        lines = so_line.read_group(domain, ["product_id", "product_uom_qty:sum"], ["product_id"], limit=limit, orderby="product_uom_qty desc")
        res = [{"product_id": rec["product_id"][0], "product_name": rec["product_id"][1], "qty": rec["product_uom_qty"]} for rec in lines if rec.get("product_id")]
        return {"company": company.name, "items": res, "start_date": _dt_str(start_date), "end_date": _dt_str(end_date)}

    def tool_count_products(self, include_services=False):
        env = self._env_for_tools()
        PT = env["product.template"]
        total_stock = PT.search_count([("active","=",True),("type","=","product")])
        total_consu = PT.search_count([("active","=",True),("type","=","consu")])
        counts = {"stockable": total_stock, "consumable": total_consu, "stockable_plus_consumable": total_stock + total_consu}
        if include_services:
            total_service = PT.search_count([("active","=",True),("type","=","service")])
            counts["service"] = total_service
            counts["all_including_service"] = counts["stockable_plus_consumable"] + total_service
        return counts

    # ---------- Generic tools (Any DB) ----------
    def tool_count_records(self, model, domain=None):
        env = self._env_for_tools()
        if model not in env:
            raise UserError(_("Unknown model: %s") % model)
        dom = domain or []
        return {"model": model, "count": env[model].search_count(dom)}

    def tool_search_read(self, model, domain=None, fields=None, limit=50, order=None):
        env = self._env_for_tools()
        if model not in env:
            raise UserError(_("Unknown model: %s") % model)
        dom = domain or []
        flds = fields or []
        recs = env[model].search(dom, limit=limit, order=order or False)
        return {"model": model, "records": recs.read(flds)}

    def tool_read_group(self, model, domain=None, fields=None, groupby=None, limit=20, orderby=None, lazy=False):
        env = self._env_for_tools()
        if model not in env:
            raise UserError(_("Unknown model: %s") % model)
        dom = domain or []
        flds = fields or []
        groups = env[model].read_group(dom, flds, groupby or [], limit=limit, orderby=orderby or False, lazy=lazy)
        return {"model": model, "groups": groups}

    def tool_list_models(self, name_like=None, limit=200):
        env = self._env_for_tools()
        M = env["ir.model"]
        dom = []
        if name_like:
            dom = ["|", ("model","ilike",name_like), ("name","ilike",name_like)]
        recs = M.search(dom, limit=limit)
        return [{"model": r.model, "name": r.name, "id": r.id} for r in recs]

    def tool_describe_model(self, model):
        env = self._env_for_tools()
        if model not in env:
            raise UserError(_("Unknown model: %s") % model)
        fields = env[model].fields_get()
        out = {}
        for k, v in fields.items():
            out[k] = {"type": v.get("type"), "string": v.get("string"), "help": v.get("help")}
        return {"model": model, "fields": out}

    # ---------- Tool registry ----------
    def execute_tool(self, name, arguments):
        tools = {
            "get_profit": lambda args: self.tool_get_profit(**args),
            "top_selling_products": lambda args: self.tool_top_selling_products(**args),
            "get_total_revenue": lambda args: self.tool_get_total_revenue(**args),
            "get_total_expense": lambda args: self.tool_get_total_expense(**args),
            "count_products": lambda args: self.tool_count_products(**args),
            "count_records": lambda args: self.tool_count_records(**args),
            "search_read": lambda args: self.tool_search_read(**args),
            "read_group": lambda args: self.tool_read_group(**args),
            "list_models": lambda args: self.tool_list_models(**args),
            "describe_model": lambda args: self.tool_describe_model(**args),
        }
        if name not in tools:
            raise UserError(_("Unknown tool: %s") % name)
        return tools[name](arguments or {})

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
            {"type": "function", "function": {
                "name": "count_products",
                "description": "Count products by type (stockable, consumable, optionally services)",
                "parameters": {"type": "object","properties": {
                    "include_services": {"type": "boolean", "default": False}
                }}
            }},
            {"type": "function", "function": {
                "name": "count_records",
                "description": "Count records in any model using a domain",
                "parameters": {"type": "object","properties": {
                    "model": {"type": "string"}, "domain": {"type": "array", "items": {"type": "array"}}
                }, "required": ["model"]}
            }},
            {"type": "function", "function": {
                "name": "search_read",
                "description": "Search any model with an Odoo domain and read selected fields",
                "parameters": {"type": "object","properties": {
                    "model": {"type": "string"}, "domain": {"type": "array", "items": {"type": "array"}},
                    "fields": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer","default":50},
                    "order": {"type": "string"}
                }, "required": ["model"]}
            }},
            {"type": "function", "function": {
                "name": "read_group",
                "description": "Aggregate any model with domain + fields + groupby",
                "parameters": {"type": "object","properties": {
                    "model": {"type": "string"}, "domain": {"type": "array", "items": {"type": "array"}},
                    "fields": {"type": "array", "items": {"type": "string"}},
                    "groupby": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer","default":20},
                    "orderby": {"type": "string"}, "lazy": {"type": "boolean", "default": False}
                }, "required": ["model","fields"]}
            }},
            {"type": "function", "function": {
                "name": "list_models",
                "description": "List available models (searchable by name)",
                "parameters": {"type": "object","properties": {
                    "name_like": {"type": "string"}, "limit": {"type": "integer","default":200}
                }}
            }},
            {"type": "function", "function": {
                "name": "describe_model",
                "description": "Describe fields of a model (type, label, help)",
                "parameters": {"type": "object","properties": {
                    "model": {"type": "string"}
                }, "required": ["model"]}
            }},
        ]
