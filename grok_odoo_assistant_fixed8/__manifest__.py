# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant — Fixed 6 (x.ai + Groq + Custom)',
    'version': '17.0.1.0.6',
    'summary': 'Text/voice assistant with safe Odoo actions. Works with x.ai Grok, Groq (OpenAI-compatible), or a custom endpoint.',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'category': 'Productivity',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/grok_assistant_views.xml'
    ],
    'installable': True,
    'application': True,
}
