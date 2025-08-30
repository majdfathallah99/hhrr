{
    "name": "AI Business Assistant v118 (Agentic Multi‑Turn + Name Guard)",
    "version": "17.0.118.0",
    "summary": "Ask anything about your Odoo data; safe generic tools + Groq defaults (OpenAI-compatible).",
    "sequence": 10,
    "category": "Productivity",
    "author": "You + ChatGPT",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": ["account", "base", "base_setup", "purchase", "sale", "sale_management", "stock", "web", "website"],
    "data": ["security/ir.model.access.csv", "views/ai_assistant_views.xml", "views/res_config_settings_ai_voice.xml", "views/voice_menu.xml", "data/ai_app_menu.xml", "data/set_groq_defaults.xml", "data/set_groq_key.xml"],
    "assets": {},
    "application": true,
    "installable": true
}
