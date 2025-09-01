# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant (Voice + Actions)',
    'version': '17.0.1.0.0',
    'summary': 'Integrate x.ai Grok with Odoo to chat by text/voice and (safely) create/read records.',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'category': 'Productivity',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/grok_assistant_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'grok_odoo_assistant/static/src/js/grok_voice.js',
        ],
        'web.assets_qweb': [
            'grok_odoo_assistant/static/src/xml/grok_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
}