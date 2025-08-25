# -*- coding: utf-8 -*-
{
    'name': 'Odoo Tasks Widget Bridge v5',
    'summary': 'JSON API + Preview page to expose Project tasks for Android widgets',
    'version': '17.0.1.0.0',
    'category': 'Project',
    'author': 'ChatGPT',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': ['project'],
    'data': [
        'views/res_users_views.xml',
        'views/preview_templates.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False
}