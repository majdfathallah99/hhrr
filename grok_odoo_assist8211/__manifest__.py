# -*- coding: utf-8 -*-
{
    "name": "Grok Odoo Assistant (Fixed)",
    "summary": "مساعد أودو عربي مع أوامر COMMAND منطقية وتصحيح تلقائي",
    "version": "18.0.1.0.0",
    "author": "ChatGPT Fix",
    "website": "https://example.com",
    "license": "LGPL-3",
    "category": "Tools",
    "depends": ["base", "web", "product", "sale_management", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "grok_odoo_assistant_f78_fixed/static/src/css/app.css",
            "grok_odoo_assistant_f78_fixed/static/src/js/app.js",
        ]
    },
    "installable": True,
    "application": True,
}
