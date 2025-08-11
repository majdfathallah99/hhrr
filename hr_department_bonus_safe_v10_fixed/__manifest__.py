
# -*- coding: utf-8 -*-
{
    "name": "HR Department Bonus",
    "version": "17.0.1.3.0",
    "summary": "Bonus requests with department budgets + optional Payroll sync (manual button)",
    "category": "Human Resources",
    "author": "ChatGPT",
    "license": "LGPL-3",
    "depends": ["hr", "mail", "hr_payroll"],
    "data": [
        "data/hr_department_bonus_sequence.xml",
        "security/hr_department_bonus_security.xml",
        "security/ir.model.access.xml",
        "views/hr_bonus_type_views.xml",
        "views/hr_bonus_request_views.xml",
        "views/hr_department_views_inherit.xml",
        "views/hr_department_bonus_menu.xml",
        "views/hr_payslip_inherit_view.xml",
        "data/hr_department_bonus_mail_templates.xml"
    ],
    "installable": True,
    "application": False
}
