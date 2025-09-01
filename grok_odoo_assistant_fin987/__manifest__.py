# -*- coding: utf-8 -*-
{
    'name': 'Grok Odoo Assistant — Ready (AR, Sanitized, Nice UI)',
    'version': '17.0.4.0.0',
    'summary': 'Arabic voice + powerful actions (SO/PO lines, products, partners). Pretty plain-HTML UI (no CSS/JSON).',
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
