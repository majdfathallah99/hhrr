# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant (Voice + Actions) — Fixed 4 (Robust JSON handling)',
    'version': '17.0.1.0.4',
    'summary': 'Grok assistant with pure-HTML UI and resilient JSON handling for /grok/chat.',
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
