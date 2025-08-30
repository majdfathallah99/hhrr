
from odoo import models, api, _ , fields
from odoo.exceptions import UserError

def _json_schema_string(desc, required=False):
    return {"type": "string","description": desc, **({"minLength": 1} if required else {})}

def _json_schema_integer(desc, required=False):
    return {"type": "integer","description": desc}

def _json_schema_number(desc):
    return {"type": "number", "description": desc}

def _json_schema_boolean(desc):
    return {"type": "boolean", "description": desc}

def _json_schema_array(item_schema, desc):
    return {"type": "array", "items": item_schema, "description": desc}


class AIBusinessToolsCore(models.AbstractModel):
    _name = "ai.business.tools.core"
    _description = "AI Business: Generic DB Tools + Create SO/PO"

    # ---- helpers ----
    def _env_effective(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param("ai_business_assistant.superuser") == "True":
            return self.env.sudo()
        return self.env

    def _resolve_partner(self, partner_id=None, partner_name=None, is_vendor=False, is_customer=False):
        env = self._env_effective()
        Partner = env['res.partner']
        partner = None
        if partner_id:
            partner = Partner.browse(int(partner_id))
            if not partner.exists():
                partner = None
        if not partner and partner_name:
            dom = [('name', 'ilike', partner_name)]
            if is_vendor: dom.append(('supplier_rank','>',0))
            if is_customer: dom.append(('customer_rank','>',0))
            partner = Partner.search(dom, limit=1)
        if not partner:
            raise UserError(_("Partner not found."))
        return partner

    def _resolve_product(self, product_id=None, default_code=None, name=None):
        env = self._env_effective()
        Product = env['product.product']
        product = None
        if product_id:
            product = Product.browse(int(product_id))
            if not product.exists():
                product = None
        if not product and default_code:
            product = Product.search([('default_code','=',default_code)], limit=1)
        if not product and name:
            product = Product.search([('name','ilike',name)], limit=1)
        if not product:
            raise UserError(_("Product not found."))
        return product

    # ---- tool schemas for function-calling ----
    @api.model
    def tool_schemas(self):
        return [
            {"type":"function","function":{"name":"count_records","description":"Count records in any model with an optional domain filter.","parameters":{"type":"object","properties":{"model":{"type":"string","description":"Model technical name, e.g., 'res.partner' or 'sale.order'","minLength":1},"domain":{"type":"array","items":{"type":"array"},"description":"Odoo domain as JSON array (e.g., [[\"customer_rank\", \">\", 0]])"}},"required":["model"]}},
            {"type":"function","function":{"name":"search_read","description":"search_read on any model.","parameters":{"type":"object","properties":{"model":{"type":"string","description":"Model technical name","minLength":1},"domain":{"type":"array","items":{"type":"array"},"description":"Odoo domain"},"fields":{"type":"array","items":{"type":"string","description":"Field name"},"description":"List of field names"},"limit":{"type":"integer","description":"Max number of records"},"order":{"type":"string","description":"Order (e.g., 'name asc')"}},"required":["model"]}},
            {"type":"function","function":{"name":"read_group","description":"Aggregation query on any model.","parameters":{"type":"object","properties":{"model":{"type":"string","description":"Model technical name","minLength":1},"domain":{"type":"array","items":{"type":"array"},"description":"Odoo domain"},"fields":{"type":"array","items":{"type":"string","description":"Field name"},"description":"Aggregation fields with :sum,:count suffix etc. (e.g., ['amount_total:sum'])"},"groupby":{"type":"array","items":{"type":"string","description":"groupby field"},"description":"Group by fields"},"limit":{"type":"integer","description":"Limit groups"},"orderby":{"type":"string","description":"Order groups"}},"required":["model","fields"]}},
            {"type":"function","function":{"name":"count_products","description":"Count stockable vs consumable products.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"create_sale_order","description":"Create a quotation/sales order. If confirm=True it will be confirmed.","parameters":{"type":"object","properties":{"partner_id":{"type":"integer","description":"Customer ID (optional)"},"partner_name":{"type":"string","description":"Customer name (optional)"},"date_order":{"type":"string","description":"Order date (YYYY-MM-DD)"},"confirm":{"type":"boolean","description":"Confirm the order after creation"},"lines":{"type":"array","items":{"type":"object","properties":{"product_id":{"type":"integer","description":"Product ID (optional)"},"default_code":{"type":"string","description":"Internal reference/SKU (optional)"},"name":{"type":"string","description":"Product name to search (optional)"},"quantity":{"type":"number","description":"Quantity"},"price_unit":{"type":"number","description":"Unit price (optional)"}},"required":["quantity"]},"description":"Sales order lines"}}}}},
            {"type":"function","function":{"name":"create_purchase_order","description":"Create a purchase order. If confirm=True it will be confirmed.","parameters":{"type":"object","properties":{"vendor_id":{"type":"integer","description":"Vendor ID (optional)"},"vendor_name":{"type":"string","description":"Vendor name (optional)"},"date_order":{"type":"string","description":"Order date (YYYY-MM-DD)"},"confirm":{"type":"boolean","description":"Confirm the PO after creation"},"lines":{"type":"array","items":{"type":"object","properties":{"product_id":{"type":"integer","description":"Product ID (optional)"},"default_code":{"type":"string","description":"SKU (optional)"},"name":{"type":"string","description":"Product name to search (optional)"},"quantity":{"type":"number","description":"Quantity"},"price_unit":{"type":"number","description":"Unit price (optional)"}}, "required":["quantity"]},"description":"Purchase order lines"}}}}},
            {"type":"function","function":{"name":"create_record","description":"Generic: create any record with given vals dict. Field names must be valid.","parameters":{"type":"object","properties":{"model":{"type":"string","description":"Model technical name","minLength":1},"vals":{"type":"object","description":"Dictionary of field values"}},"required":["model","vals"]}}},
            {"type":"function","function":{"name":"update_record","description":"Generic: write on an existing record id with vals.","parameters":{"type":"object","properties":{"model":{"type":"string","description":"Model","minLength":1},"id":{"type":"integer","description":"Record ID"},"vals":{"type":"object","description":"Dictionary of field values"}},"required":["model","id","vals"]}}},
            {"type":"function","function":{"name":"delete_record","description":"Generic: unlink a record by id.","parameters":{"type":"object","properties":{"model":{"type":"string","description":"Model","minLength":1},"id":{"type":"integer","description":"Record ID"}},"required":["model","id"]}}},
        ]

    # ---- tool executor ----
    @api.model
    def execute_tool(self, name, args=None):
        args = args or {}
        fn = getattr(self, f"_tool__{name}", None)
        if not fn:
            raise UserError(_("Unknown tool: %s") % name)
        return fn(**args)

    # ---- implementations ----
    def _tool__count_products(self):
        env = self._env_effective()
        Product = env['product.product']
        stockable = Product.search_count([('detailed_type','=','product')])
        consumable = Product.search_count([('detailed_type','=','consumable')])
        return {"stockable": stockable,"consumable": consumable,"stockable_plus_consumable": stockable + consumable}

    def _coerce_domain(self, domain):
        if isinstance(domain, list):
            return domain
        return []

    def _tool__count_records(self, model, domain=None):
        env = self._env_effective()
        Model = env[model]
        return {"model": model, "count": Model.search_count(self._coerce_domain(domain))}

    def _tool__search_read(self, model, domain=None, fields=None, limit=None, order=None):
        env = self._env_effective()
        Model = env[model]
        records = Model.search(self._coerce_domain(domain or []), limit=limit, order=order)
        data = records.read(fields) if fields else records.read()
        return {"model": model, "size": len(data), "records": data}

    def _tool__read_group(self, model, domain=None, fields=None, groupby=None, limit=None, orderby=None):
        env = self._env_effective()
        Model = env[model]
        res = Model.read_group(self._coerce_domain(domain or []), fields or [], groupby or [], limit=limit, orderby=orderby)
        return {"model": model, "groups": res}

    def _tool__create_record(self, model, vals):
        env = self._env_effective()
        rec = env[model].create(vals or {})
        return {"model": model, "id": rec.id}

    def _tool__update_record(self, model, id, vals):
        env = self._env_effective()
        rec = env[model].browse(int(id))
        rec.write(vals or {})
        return {"model": model, "id": rec.id, "updated": True}

    def _tool__delete_record(self, model, id):
        env = self._env_effective()
        rec = env[model].browse(int(id))
        rec.unlink()
        return {"model": model, "id": int(id), "deleted": True}

    def _tool__create_sale_order(self, partner_id=None, partner_name=None, date_order=None, confirm=False, lines=None):
        env = self._env_effective()
        partner = self._resolve_partner(partner_id, partner_name, is_customer=True)
        so_vals = {"partner_id": partner.id}
        if date_order: so_vals["date_order"] = date_order
        SaleOrder = env['sale.order']
        so = SaleOrder.create(so_vals)
        lines = lines or []
        for ln in lines:
            product = self._resolve_product(ln.get("product_id"), ln.get("default_code"), ln.get("name"))
            qty = ln.get("quantity") or 1.0
            price = ln.get("price_unit")
            # emulate onchange for defaults
            sol_vals = {
                "order_id": so.id,
                "product_id": product.id,
                "name": product.display_name,
                "product_uom_qty": qty,
                "price_unit": price if price is not None else product.lst_price,
            }
            env['sale.order.line'].create(sol_vals)
        if confirm:
            so.action_confirm()
        return {"sale_order_id": so.id, "name": so.name, "state": so.state}

    def _tool__create_purchase_order(self, vendor_id=None, vendor_name=None, date_order=None, confirm=False, lines=None):
        env = self._env_effective()
        vendor = self._resolve_partner(vendor_id, vendor_name, is_vendor=True)
        po_vals = {"partner_id": vendor.id}
        if date_order: po_vals["date_order"] = date_order
        PO = env['purchase.order']
        po = PO.create(po_vals)
        lines = lines or []
        for ln in lines:
            product = self._resolve_product(ln.get("product_id"), ln.get("default_code"), ln.get("name"))
            qty = ln.get("quantity") or 1.0
            price = ln.get("price_unit")
            pol_vals = {
                "order_id": po.id,
                "product_id": product.id,
                "name": product.display_name,
                "product_qty": qty,
                "product_uom": product.uom_po_id.id or product.uom_id.id,
                "price_unit": price if price is not None else product.standard_price,
                "date_planned": fields.Datetime.now(),
            }
            env['purchase.order.line'].create(pol_vals)
        if confirm:
            po.button_confirm()
        return {"purchase_order_id": po.id, "name": po.name, "state": po.state}
