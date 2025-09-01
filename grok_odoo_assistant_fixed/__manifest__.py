# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant (Voice + Actions) — Fixed',
    'version': '17.0.1.0.1',
    'summary': 'x.ai Grok assistant with simple voice UI and safe DB actions. Includes standalone settings wizard.',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'category': 'Productivity',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/grok_assistant_views.xml',
        'views/grok_config_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'grok_odoo_assistant_fixed/static/src/js/grok_voice.js',
        ],
        'web.assets_qweb': [
            'grok_odoo_assistant_fixed/static/src/xml/grok_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
}