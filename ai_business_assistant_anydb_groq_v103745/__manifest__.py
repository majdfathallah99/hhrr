{
    'name': 'AI Business Assistant (Any DB)',
    'summary': 'Ask anything about your Odoo data; safe generic tools + Groq defaults (OpenAI-compatible).',
    'version': '17.0.3.1',
    'author': 'You + ChatGPT',
    'website': 'https://example.com',
    'category': 'Productivity',
    'license': 'LGPL-3',
    'depends': ['base_setup', 'sale', 'purchase', 'website', 'base', 'bus', 'account', 'sale_management', 'stock', 'web', 'mail'],
    'data': ['data/set_groq_key.xml', 'security/ir.model.access.csv', 'data/ai_app_menu.xml', 'data/set_groq_defaults.xml', 'views/ai_voice_views.xml'],
    'assets': {'web.assets_backend': ['static/src/js/voice_chat_client.js', 'static/src/scss/voice.scss'], 'web.assets_qweb': ['static/src/xml/voice_templates.xml']},
    'application': True,
    'installable': True,
}