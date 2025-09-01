# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant (Voice + Actions) — Fixed 2',
    'version': '17.0.1.0.2',
    'summary': 'x.ai Grok assistant with simple voice UI and safe DB actions. Server QWeb template fix.',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'category': 'Productivity',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/grok_assistant_views.xml',
        'views/grok_config_views.xml',
        'views/grok_ui_templates.xml',  # moved to server-rendered QWeb
    ],
    'assets': {
        'web.assets_backend': [
            'grok_odoo_assistant_fixed2/static/src/js/grok_voice.js',
        ],
        # no assets_qweb needed for server-side rendering
    },
    'installable': True,
    'application': True,
}