
import json, ast
from datetime import datetime, timedelta
from odoo import models, api

class AIBusinessToolsCore(models.AbstractModel):
    _name = "ai.business.tools.core"
    _description = "AI Business Tools Core"

    # ---------- helpers ----------
    def _coerce_domain(self, domain):
        if not domain:
            return []
        if isinstance(domain, list):
            return domain
        if isinstance(domain, str):
            try:
                return json.loads(domain)
            except Exception:
                try:
                    return ast.literal_eval(domain)
                except Exception:
                    return []
        return []

    def _coerce_lines(self, lines):
        if not lines:
            return []
        if isinstance(lines, list):
            return lines
        if isinstance(lines, str):
            try:
                return json.loads(lines)
            except Exception:
                try:
                    return ast.literal_eval(lines)
                except Exception:
                    return []
        return []

    def _find_partner(self, partner_id=None, partner_name=None, is_vendor=False):
        Partner = self.env["res.partner"].sudo()
        if partner_id:
            p = Partner.browse(int(partner_id))
            if p.exists():
                return p
        if partner_name:
            dom = [("name", "ilike", partner_name)]
            if is_vendor:
                dom.append(("supplier_rank", ">", 0))
            else:
                dom.append(("customer_rank", ">", 0))
            p = Partner.search(dom, limit=1)
            if p:
                return p
        return None

    def _find_product(self, product_id=None, default_code=None, name=None):
        Product = self.env["product.product"].sudo()
        if product_id:
            p = Product.browse(int(product_id))
            if p.exists():
                return p
        if default_code:
            p = Product.search([("default_code", "=", default_code)], limit=1)
            if p:
                return p
        if name:
            p = Product.search([("name", "ilike", name)], limit=1)
            if p:
                return p
        return None

    # ---------- schemas for function calling ----------
    def tool_schemas(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "count_products",
                    "description": "Return counts of stockable and consumable products.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "count_records",
                    "description": "Count records in any model with an optional Odoo domain.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string", "description": "Model name, e.g., 'res.partner'"},
                            "domain": {
                                "description": "Odoo domain as JSON array or string that parses to a list.",
                                "anyOf": [{"type": "array"}, {"type": "string"}]
                            }
                        },
                        "required": ["model"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_sale_order",
                    "description": "Create a sales order. If missing info, the tool will raise an error rather than guessing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"anyOf":[{"type":"integer"},{"type":"null"}]},
                            "customer_name": {"anyOf":[{"type":"string"},{"type":"null"}]},
                            "date_order": {"anyOf":[{"type":"string"},{"type":"null"}], "description":"YYYY-MM-DD"},
                            "lines": {
                                "anyOf":[{"type":"array"},{"type":"string"},{"type":"null"}],
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "product_id": {"anyOf":[{"type":"integer"},{"type":"null"}]},
                                        "default_code": {"anyOf":[{"type":"string"},{"type":"null"}]},
                                        "name": {"anyOf":[{"type":"string"},{"type":"null"}]},
                                        "quantity": {"type": "number"},
                                        "price_unit": {"anyOf":[{"type":"number"},{"type":"null"}]}
                                    },
                                    "required": ["quantity"]
                                }
                            },
                            "confirm": {"type": "boolean", "description": "Confirm the order after creation."}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_sale_order",
                    "description": "Delete a sales order by ID or name. If neither provided, will delete the most recent draft SO.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_purchase_order",
                    "description": "Create a purchase order. Lines must be an array.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vendor_id": {"anyOf":[{"type":"integer"},{"type":"null"}]},
                            "vendor_name": {"anyOf":[{"type":"string"},{"type":"null"}]},
                            "date_order": {"anyOf":[{"type":"string"},{"type":"null"}], "description":"YYYY-MM-DD"},
                            "lines": {"anyOf":[{"type":"array"},{"type":"string"},{"type":"null"}], "items":,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "product_id": {"type": "integer"},
                                        "default_code": {"type": "string"},
                                        "name": {"type": "string"},
                                        "quantity": {"type": "number"},
                                        "price_unit": {"type": "number"}
                                    },
                                    "required": ["quantity"]
                                }
                            },
                            "confirm": {"type": "boolean"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_purchase_order",
                    "description": "Delete a purchase order by ID or name. If neither provided, will delete the most recent draft PO.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"}
                        }
                    }
                }
            },
        ]

    # ---------- executor ----------
    def execute_tool(self, name, args):
        name = (name or "").strip()
        args = args or {}
        if name == "count_products":
            return self._count_products()
        if name == "count_records":
            return self._count_records(args.get("model"), args.get("domain"))
        if name == "create_sale_order":
            return self._create_sale_order(args)
        if name == "delete_sale_order":
            return self._delete_sale_order(args.get("id"), args.get("name"))
        if name == "create_purchase_order":
            return self._create_purchase_order(args)
        if name == "delete_purchase_order":
            return self._delete_purchase_order(args.get("id"), args.get("name"))
        raise ValueError("Unknown tool: %s" % name)

    # ---------- tool implementations ----------
    def _count_products(self):
        Prod = self.env["product.product"].sudo()
        stockable = Prod.search_count([("detailed_type", "=", "product")])
        consumable = Prod.search_count([("detailed_type", "=", "consu")])
        return {"stockable": stockable, "consumable": consumable, "stockable_plus_consumable": stockable + consumable}

    def _count_records(self, model, domain=None):
        if not model:
            raise ValueError("Missing 'model'")
        dom = self._coerce_domain(domain)
        return {"model": model, "domain": dom, "count": self.env[model].sudo().search_count(dom)}

    def _create_sale_order(self, params):
        params = dict(params or {})
        lines = self._coerce_lines(params.get("lines"))
        partner = self._find_partner(params.get("customer_id"), params.get("customer_name"), is_vendor=False)
        if not partner:
            raise ValueError("Missing or unknown customer (provide customer_id or customer_name)")
        if not lines:
            raise ValueError("Lines must be a non-empty array")
        date_order = params.get("date_order") or datetime.utcnow().strftime("%Y-%m-%d")

        order_vals = {"partner_id": partner.id, "date_order": date_order}
        line_vals = []
        for l in lines:
            qty = float(l.get("quantity") or 0)
            if qty <= 0:
                raise ValueError("Each line must have a positive quantity")
            prod = self._find_product(l.get("product_id"), l.get("default_code"), l.get("name"))
            name = l.get("name") or (prod.display_name if prod else "Item")
            price = float(l.get("price_unit") or (prod.lst_price if prod else 0.0))
            if prod:
                line_vals.append((0, 0, {
                    "product_id": prod.id,
                    "name": name,
                    "product_uom_qty": qty,
                    "price_unit": price,
                }))
            else:
                # allow service lines without product
                line_vals.append((0, 0, {
                    "name": name,
                    "product_uom_qty": qty,
                    "price_unit": price,
                }))

        order_vals["order_line"] = line_vals
        SO = self.env["sale.order"].sudo().create(order_vals)
        if params.get("confirm"):
            try:
                SO.action_confirm()
            except Exception:
                pass
        return {
            "id": SO.id, "name": SO.name, "state": SO.state, "date_order": str(SO.date_order),
            "partner": SO.partner_id.display_name,
            "lines": [{"name": l.name, "product": l.product_id.display_name, "qty": l.product_uom_qty, "price_unit": l.price_unit} for l in SO.order_line],
        }

    def _delete_sale_order(self, id=None, name=None):
        SO = self.env["sale.order"].sudo()
        rec = None
        if id:
            rec = SO.browse(int(id))
            rec = rec if rec.exists() else None
        elif name:
            rec = SO.search([("name", "=", name)], limit=1)
        else:
            # fallback: latest draft
            rec = SO.search([("state", "=", "draft")], order="create_date desc", limit=1)
        if not rec:
            return {"deleted": False, "reason": "Not found."}
        rec.unlink()
        return {"deleted": True, "name": rec.name, "id": rec.id}

    def _create_purchase_order(self, params):
        params = dict(params or {})
        lines = self._coerce_lines(params.get("lines"))
        partner = self._find_partner(params.get("vendor_id"), params.get("vendor_name"), is_vendor=True)
        if not partner:
            raise ValueError("Missing or unknown vendor (provide vendor_id or vendor_name)")
        if not lines:
            raise ValueError("Lines must be a non-empty array")
        date_order = params.get("date_order") or datetime.utcnow().strftime("%Y-%m-%d")

        POModel = self.env["purchase.order"].sudo()
        order_vals = {"partner_id": partner.id, "date_order": date_order}
        line_vals = []
        for l in lines:
            qty = float(l.get("quantity") or 0)
            if qty <= 0:
                raise ValueError("Each line must have a positive quantity")
            prod = self._find_product(l.get("product_id"), l.get("default_code"), l.get("name"))
            name = l.get("name") or (prod.display_name if prod else "Item")
            price = float(l.get("price_unit") or (prod.standard_price if prod else 0.0))
            if prod:
                uom = prod.uom_po_id or prod.uom_id
                line_vals.append((0, 0, {
                    "product_id": prod.id,
                    "name": name,
                    "product_qty": qty,
                    "price_unit": price,
                    "product_uom": uom.id,
                }))
            else:
                # allow description-only lines
                line_vals.append((0, 0, {
                    "name": name,
                    "product_qty": qty,
                    "price_unit": price,
                }))
        order_vals["order_line"] = line_vals
        PO = POModel.create(order_vals)
        if params.get("confirm"):
            try:
                PO.button_confirm()
            except Exception:
                pass
        return {
            "id": PO.id, "name": PO.name, "state": PO.state, "date_order": str(PO.date_order),
            "partner": PO.partner_id.display_name,
            "lines": [{"name": l.name, "product": l.product_id.display_name, "qty": l.product_qty, "price_unit": l.price_unit} for l in PO.order_line],
        }

    def _delete_purchase_order(self, id=None, name=None):
        PO = self.env["purchase.order"].sudo()
        rec = None
        if id:
            rec = PO.browse(int(id))
            rec = rec if rec.exists() else None
        elif name:
            rec = PO.search([("name", "=", name)], limit=1)
        else:
            rec = PO.search([("state", "=", "draft")], order="create_date desc", limit=1)
        if not rec:
            return {"deleted": False, "reason": "Not found."}
        rec.unlink()
        return {"deleted": True, "name": rec.name, "id": rec.id}
