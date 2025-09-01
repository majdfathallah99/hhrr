{
    "name": "Grok Odoo Assistant Pro (AR/EN, Safer Tools)",
    "summary": "Bilingual assistant with voice (Arabic & English), safer tool execution and natural conversations.",
    "version": "17.0.1.0.5",
    "category": "Productivity/AI",
    "depends": ["base", "web", "sale_management", "purchase", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
        "views/session_views.xml",
        "views/ui_templates.xml",
        "views/config_templates.xml"
    ],
    "assets": {},  # keep zero assets; inline HTML/JS
    "license": "LGPL-3",
    "application": True,
    "installable": True,
}
