# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant (Voice + Actions) — Fixed 3 (No QWeb/Assets)',
    'version': '17.0.1.0.3',
    'summary': 'x.ai Grok assistant with voice + safe DB actions. Pure HTML response (no QWeb or assets).',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'category': 'Productivity',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/grok_assistant_views.xml',
        'views/grok_config_views.xml'
    ],
    'installable': True,
    'application': True,
}
