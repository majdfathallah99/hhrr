{
    "name": "Grok Odoo Assistant Pro (No JSON, No CSS)",
    "version": "17.0.2.0.1",
    "summary": "Minimal assistant UI without JSON/JS/CSS; simple POST round-trip",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
        "views/ui_templates.xml",
        "views/config_templates.xml",
        "views/session_views.xml"
    ],
    "application": True,
    "installable": True,
    "license": "LGPL-3"
}