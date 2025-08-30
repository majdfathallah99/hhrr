# -*- coding: utf-8 -*-
{
    "name": "AI Business Assistant v118 (Agentic Multi‑Turn + Name Guard)",
    "summary": "Ask anything about your Odoo data; safe generic tools + Groq defaults (OpenAI-compatible).",
    "version": "17.0.118.0",
    "author": "You + ChatGPT",
    "license": "LGPL-3",
    "depends": [
        "account",
        "base",
        "base_setup",
        "purchase",
        "sale",
        "sale_management",
        "stock",
        "web",
        "website"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/set_groq_defaults.xml",
        "data/set_groq_key.xml",
        "data/ai_app_menu.xml",
        "data/voice_menu.xml",
        "views/assets.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "ai_business_assistant_anydb_v116/static/src/js/voice_systray.js",
            "ai_business_assistant_anydb_v116/static/src/scss/voice.scss",
            "ai_business_assistant_anydb_v116/static/src/xml/voice_templates.xml"
        ]
    },
    "installable": True,
    "application": True
}