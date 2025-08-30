{
  "name": "AI Business Assistant v118 (Agentic Multi\u2011Turn + Name Guard)",
  "version": "17.0.118.0",
  "summary": "Ask anything about your Odoo data; safe generic tools + Groq defaults (OpenAI-compatible).",
  "author": "You + ChatGPT",
  "category": "Productivity",
  "license": "LGPL-3",
  "website": "https://example.com",
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
    "data/voice_menu.xml"
  ],
  "installable": true,
  "application": true
}