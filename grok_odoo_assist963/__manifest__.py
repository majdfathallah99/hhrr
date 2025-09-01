# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant — Fallback (AR, No CSS/JSON)',
    'version': '17.0.5.0.0',
    'summary': 'Arabic voice + powerful actions with safe fallbacks. Plain-HTML UI (no CSS/JSON).',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'category': 'Productivity',
    'depends': ['base', 'web', 'sale_management', 'purchase', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml'
    ],
    'installable': True,
    'application': True
}
