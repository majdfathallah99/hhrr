# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant — Final (No CSS/JSON UI)',
    'version': '17.0.2.0.0',
    'summary': 'Voice assistant for Odoo with safe DB actions. Plain HTML UI (no CSS, no JSON-RPC).',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'category': 'Productivity',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml'
    ],
    'installable': True,
    'application': True
}
