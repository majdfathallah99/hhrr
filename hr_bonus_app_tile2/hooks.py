
# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _grant(env, "hr.bonus.type", "Bonus Type access")
    _grant(env, "hr.bonus.request", "Bonus Request access")

def _grant(env, model_name, name):
    m = env['ir.model']._get(model_name)
    if not m:
        return
    group = env.ref('base.group_user')
    access = env['ir.model.access']
    if not access.search([('model_id','=',m.id),('group_id','=',group.id)], limit=1):
        access.create({
            'name': name,
            'model_id': m.id,
            'group_id': group.id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': True,
        })
