{
    "name": "AI Business Assistant (Voice + Analytics)",
    "version": "17.0.1.0.1",
    "summary": "Ask natural language questions about your Odoo data. Optional live voice chat.",
    "author": "You + ChatGPT",
    "category": "Productivity",
    "license": "LGPL-3",
    "website": "https://example.com",
    "depends": ["base", "web", "account", "sale", "stock", "website"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/ai_assistant_views.xml",
        "views/website_template.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "ai_business_assistant/static/src/js/ai_voice_widget.js"
        ]
    },
    "installable": true,
    "application": true
}