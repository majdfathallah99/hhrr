{
    'name': 'AI Business Assistant (Minimal, No Website)',
    'version': '17.0.1.0.3',
    'summary': 'Ask natural language questions about your Odoo data (no Website assets).',
    'author': 'You + ChatGPT',
    'category': 'Productivity',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'depends': ['base', 'web', 'account', 'sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_assistant_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
}