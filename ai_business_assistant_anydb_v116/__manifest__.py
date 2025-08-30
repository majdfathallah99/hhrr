{
    "name": "AI Business Assistant (AnyDB)",
    "version": "17.0.1.0",
    "summary": "AI assistant with live voice chat",
    "sequence": 10,
    "category": "Productivity",
    "author": "You + ChatGPT",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": ["base", "web", "website", "base_setup"],
    "data": ["security/ir.model.access.csv", "views/ai_assistant_views.xml", "views/res_config_settings_ai_voice.xml", "views/voice_menu.xml", "data/ai_app_menu.xml", "data/set_groq_defaults.xml", "data/set_groq_key.xml"],
    "assets": {},
    "application": true,
    "installable": true
}
