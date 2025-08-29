# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import ValidationError
import base64

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_send_whatsapp_text(self):
        """
        يفتح نافذة الإرسال المنبثقة للسماح للمستخدم بكتابة وتعديل رسالة نصية.
        """
        self.ensure_one()
    
        if self.state != 'done':
            raise ValidationError("A message can only be sent if the salary slip is in 'Done' status.")
    
        employee = self.employee_id
        if not employee:
            raise ValidationError("This payslip is not associated with any employee.")
    
        # البحث عن رقم الهاتف
        phone = (
            (employee.user_id.partner_id.mobile or employee.user_id.partner_id.phone)
            if employee.user_id and employee.user_id.partner_id else None
        ) or employee.work_phone or employee.mobile_phone
    
        if not phone:
            # ✅ تم إصلاح الخطأ هنا بإضافة علامة الاقتباس المفقودة
            raise ValidationError('There is no phone number registered for this employee.')
    
        # إعداد نص الرسالة الافتراضي
        message_body = f"Hello {employee.name},\n\nYour salary for the month {self.date_to.strftime('%B %Y')} has been disbursed.\n\nThank you."
    
        # فتح نافذة الإرسال المنبثقة
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send WhatsApp Message',
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phone': phone,
                'default_body': message_body,
            }
        }

    def action_send_whatsapp_pdf_direct(self):
        """
        يقوم بتوليد PDF وإرساله مباشرة في الخلفية دون إظهار نافذة منبثقة.
        """
        self.ensure_one()
    
        if self.state != 'done':
            raise ValidationError("The salary slip can only be sent if it is in 'Done' status.")
    
        employee = self.employee_id
        if not employee:
            raise ValidationError("This payslip is not associated with any employee.")
    
        # البحث عن رقم الهاتف
        phone = (
            (employee.user_id.partner_id.mobile or employee.user_id.partner_id.phone)
            if employee.user_id and employee.user_id.partner_id else None
        ) or employee.work_phone or employee.mobile_phone
    
        if not phone:
            raise ValidationError("There is no phone number registered for this employee.")
    
        # 1. توليد محتوى التقرير (Payslip) كـ PDF بالطريقة الصحيحة
        report_xml_id = 'hr_payroll.action_report_payslip'
        pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(report_ref=report_xml_id, res_ids=self.ids)
    
        # 2. إعداد نص الرسالة
        message_body = f"Hello {employee.name},\n\nAttached is your salary slip for the month {self.date_to.strftime('%B %Y')}.\n\nThank you."
        
        # 3. إنشاء سجل رسالة واتساب صادرة (adv.whatsapp.out)
        whatsapp_message = self.env['adv.whatsapp.out'].create({
            'type': 'media',
            'phone': phone,
            'body': message_body,
            'media': base64.b64encode(pdf_content),
            'media_filename': f"Payslip_{employee.name}_{self.date_to.strftime('%B-%Y')}.pdf",
            'status': 'pending',
        })
    
        # 4. محاولة إرسال الرسالة فورًا
        whatsapp_message.action_send_whatsapp()
    
        # 5. عرض إشعار نجاح للمستخدم
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Done Successfully',
                'message': f"The payslip has been scheduled for sending to {phone}.",
                'type': 'success',
                'sticky': False,
            }
        }
