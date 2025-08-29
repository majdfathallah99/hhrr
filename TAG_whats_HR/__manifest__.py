{
    "name": "Tag_Whatsapp_for_HR",
    "version": "1.0.0",
    "category": "Tools",
    "summary": "Send WhatsApp via WasenderAPI ",
    "author": "Tag Technology",
    "depends": ["base", "mail" ,"hr_payroll"],
    'data': [
        'security/ir.model.access.csv',
        'data/scheduled_actions.xml',
        'views/adv_whatsapp_out_views.xml', 
        'views/hr_payslip_views.xml' ,
        "views/whatsapp_composer_view.xml"

    ],
    'installable': True,
    'application': True,
}