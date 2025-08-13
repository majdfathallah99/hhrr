
# -*- coding: utf-8 -*-
{
    "name": "HR Bonuses",
    "version": "17.0.4.0.0",
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
        "views/menu.xml"
    ],
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True,
}
