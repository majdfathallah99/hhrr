# -*- coding: utf-8 -*-
{
    'name': 'Odoo Tasks Widget Bridge v8',
    'summary': 'Home-screen app + JSON API + Saved items for Android widgets',
    'version': '17.0.2.0.1',
    'category': 'Project',
    'author': 'ChatGPT',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/task_widget_item_views.xml',
        'views/menu.xml',
        'data/cron.xml'
    ],
    'installable': True,
    'application': True
}