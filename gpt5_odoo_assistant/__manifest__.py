
# -*- coding: utf-8 -*-


{'name': 'GPT-5 Odoo Assistant',
 'summary': 'Agent-mode AI assistant integrated with OpenAI (GPT-5) with safe tool access to your Odoo data',
 'version': '17.0.1.0.0',
 'category': 'Productivity/AI',
 'author': 'ChatGPT',
 'license': 'LGPL-3',
 'website': 'https://example.com',
 'depends': ['base','web'],
 'data': [
    'security/security.xml',
    'security/ir.model.access.csv',
    'views/menu.xml',
    'views/gpt_thread_views.xml',
    'views/res_config_settings_views.xml',
    'data/ir_cron.xml',
 ],
 'assets': {
    'web.assets_backend': [
       # minimal assets placeholder (no JS required to run basic UI)
    ],
 },
 'external_dependencies': {
     'python': ['requests']
 },
 'installable': True,
 'application': True,
 'auto_install': False,
}
