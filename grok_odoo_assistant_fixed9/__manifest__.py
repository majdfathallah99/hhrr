# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant — Fixed 8 (Patched, x.ai + Groq + Custom)',
    'version': '17.0.1.0.8',
    'summary': 'Assistant with voice + safe Odoo actions. Providers: x.ai, Groq, Custom. (Patched indentation)',
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
