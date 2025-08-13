
# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _ensure_access(env, "hr.bonus.type", "access_hr_bonus_type_user")
    _ensure_access(env, "hr.bonus.request", "access_hr_bonus_request_user")

def _ensure_access(env, model_name, access_name):
    IrModel = env['ir.model']
    IrAccess = env['ir.model.access']
    model = IrModel._get(model_name)
    if not model:
        return
    group = env.ref('base.group_user')
    if not IrAccess.search([('model_id','=',model.id),('group_id','=',group.id)], limit=1):
        IrAccess.create({
            'name': access_name,
            'model_id': model.id,
            'group_id': group.id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': True,
        })
