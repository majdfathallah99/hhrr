from odoo import models
from odoo.exceptions import ValidationError
import base64


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_send_whatsapp_payslip(self):
        for payslip in self:
            if payslip.state != 'done':
                raise ValidationError("The salary slip cannot be sent until it is in 'Done' status.")

            employee = payslip.employee_id
            partner = employee.user_id.partner_id or employee.address_id

            if not partner:
                raise ValidationError('Employee has no contact (Partner).')

            phone = (
                (employee.user_id.partner_id.mobile or employee.user_id.partner_id.phone)
                if employee.user_id and employee.user_id.partner_id else None
            ) or employee.work_phone or employee.mobile_phone

            if not phone:
                raise ValidationError('The employee does not have a phone number.')

            return {
                'type': 'ir.actions.act_window',
                'name': 'Send WhatsApp',
                'res_model': 'whatsapp.composer',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_phone': phone,
                    'default_body': f'Hello {employee.name}, Your salary for the month of {payslip.date_from.strftime("%B %Y")} has been disbursed.',
                    'default_type': 'text',
                }
            }

    def action_send_whatsapp_payslip_pdf(self):
        for payslip in self:
            if payslip.state != 'done':
                raise ValidationError("The salary slip can only be sent after it is in 'Done' status.")

            employee = payslip.employee_id
            partner = employee.user_id.partner_id or employee.address_id

            if not partner:
                raise ValidationError('The employee does not have a contact (Partner).')

            phone = (
                (employee.user_id.partner_id.mobile or employee.user_id.partner_id.phone)
                if employee.user_id and employee.user_id.partner_id else None
            ) or employee.work_phone or employee.mobile_phone

            if not phone:
                raise ValidationError('The employee does not have a phone number.')

            # Generate PDF
            report_service = self.env['ir.actions.report']
            pdf_content, _ = report_service._render_qweb_pdf('hr_payroll.action_report_payslip', [payslip.id])
            pdf_base64 = base64.b64encode(pdf_content)

            # TODO: هنا تقدر تستدعي ميثود الإرسال بالواتساب مع الـ pdf_base64

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Quote sent to {phone} successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }

