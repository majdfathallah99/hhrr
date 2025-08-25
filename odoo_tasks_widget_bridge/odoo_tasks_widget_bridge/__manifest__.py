# -*- coding: utf-8 -*-
{
    "name": "Odoo Tasks Widget Bridge",
    "summary": "Adds 'My Tasks' app and a simple JSON endpoint for an Android home-screen widget.",
    "version": "17.0.1.0.0",
    "category": "Productivity",
    "author": "You",
    "license": "LGPL-3",
    "depends": ["base", "web", "project"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/res_users_views.xml",
    ],
    "assets": {},
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": True,
}
