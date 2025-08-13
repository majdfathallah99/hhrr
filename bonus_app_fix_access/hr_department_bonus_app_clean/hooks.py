
# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Ensure access for hr.bonus.type
    _ensure_access(env, model_name="hr.bonus.type", access_xmlid="access_hr_bonus_type_user")
    # Ensure access for hr.bonus.request
    _ensure_access(env, model_name="hr.bonus.request", access_xmlid="access_hr_bonus_request_user")

def _ensure_access(env, model_name, access_xmlid):
    IrModel = env['ir.model']
    IrAccess = env['ir.model.access']
    model = IrModel._get(model_name)
    if not model:
        return
    # If already exists, skip
    if IrAccess.search([('model_id', '=', model.id), ('group_id', '=', env.ref('base.group_user').id)], limit=1):
        return
    IrAccess.create({
        'name': access_xmlid,
        'model_id': model.id,
        'group_id': env.ref('base.group_user').id,
        'perm_read': True,
        'perm_write': True,
        'perm_create': True,
        'perm_unlink': True,
    })
