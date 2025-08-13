
# -*- coding: utf-8 -*-
{
    "name": "HR Department Bonus (App)",
    "version": "17.0.3.0.0",
    "summary": "Standalone Bonuses app: requests & department budgets",
    "category": "Human Resources",
    "author": "You",
    "license": "LGPL-3",
    "images": ["static/description/icon.png"],
    "depends": ["hr", "mail"],
    "data": [
        "data/hr_department_bonus_sequence.xml",
        
        "views/hr_bonus_type_views.xml",
        "views/hr_bonus_request_views.xml",
        "views/hr_department_views_inherit.xml",
        "views/hr_department_bonus_menu.xml"
    ],
    "application": True,
    "installable": True,,
    "post_init_hook": "post_init_hook"
}
