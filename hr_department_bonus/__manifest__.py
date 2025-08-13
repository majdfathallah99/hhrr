
# -*- coding: utf-8 -*-
{
    "name": "HR Department Bonus",
    "version": "17.0.1.0.8",
    "summary": "Request, approve, and pay employee bonuses with department budgets (Time Off-like flow) + optional Payroll input",
    "category": "Human Resources",
    "author": "ChatGPT",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": ["hr", "mail", "hr_payroll"],  # Payroll is optional; integration auto-detects
    "data": [
        "data/hr_department_bonus_sequence.xml",
        "security/hr_department_bonus_security.xml",
        "security/ir.model.access.xml",
        "views/hr_bonus_type_views.xml",
        "views/hr_bonus_request_views.xml",
        "views/hr_department_views_inherit.xml",
        "views/hr_department_bonus_menu.xml",
        "data/hr_department_bonus_mail_templates.xml"
    ],
    "installable": True,
    "application": False,
}
