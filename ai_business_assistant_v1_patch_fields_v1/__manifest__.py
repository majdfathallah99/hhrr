{
    'name': 'AI Business Assistant V1 – Settings Fields Patch',
    'summary': 'Adds missing ResConfigSettings fields (ai_enabled, ai_superuser_mode, ai_provider, ai_model) so V1 settings view loads on Odoo 17.',
    'version': '17.0.1.0',
    'category': 'Tools',
    'author': 'You + ChatGPT',
    'license': 'LGPL-3',
    'depends': ['base'],  # Install before ai_business_assistant_v1
    'data': [],
    'installable': True,
    'application': False,
}
