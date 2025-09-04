# -*- coding: utf-8 -*-
{
    "name": "GPT-5 AI Assistant",
    "summary": "ChatGPT-style assistant inside Odoo (17/18). Ask about sales, inventory, create records, etc.",
    "version": "18.0.1.0.1",
    "category": "Productivity",
    "author": "You + ChatGPT",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/templates.xml",
        "views/res_config_settings_view.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "gpt5_ai_assistant/static/src/js/chat.js",
            "gpt5_ai_assistant/static/src/xml/chat_template.xml"
        ]
    },
    "installable": True,
    "application": True,
}
