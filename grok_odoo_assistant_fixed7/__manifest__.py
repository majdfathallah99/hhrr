# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant (Voice + Actions) — Fixed 5 (Built-in Config Page)',
    'version': '17.0.1.0.5',
    'summary': 'Adds /grok/config page to set x.ai API key + options. No QWeb or assets.',
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
