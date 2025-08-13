
{
    "name": "HR Bonuses (Tile2 Fixed)",
    "version": "17.0.5.0.0",
    "summary": "Bonuses app: requests & department budgets",
    "category": "Human Resources",
    "author": "You",
    "license": "LGPL-3",
    "images": ["static/description/icon.png"],
    "depends": ["hr", "mail"],
    "data": [
        "data/seq.xml",
        "views/type_views.xml",
        "views/request_views.xml",
        "views/department_views.xml",
        "views/menu.xml"
    ],
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True
}
