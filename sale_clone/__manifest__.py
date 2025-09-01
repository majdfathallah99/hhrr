{
    "name": "Sales Clone",
    "version": "1.0",
    "summary": "Cloned version of Odoo 18 Sales Module",
    "category": "Sales",
    "depends": ["sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml"
    ],
    "installable": True,
    "application": True,
}