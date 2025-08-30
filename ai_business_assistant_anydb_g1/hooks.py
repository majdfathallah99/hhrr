from odoo import api, SUPERUSER_ID

SETTINGS_XPATH = '<xpath expr="//div[hasclass(\'settings\')]" position="inside">\n    <div class="app_settings_block o_app" data-key="ai_voice" data-string="Live Voice Chat" string="Live Voice Chat">\n        <h2>Live Voice Chat</h2>\n        <div class="row mt16 o_settings_container">\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_voice_enabled" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_voice_enabled"/>\n                    <div class="text-muted">Enable built-in WebRTC voice rooms with Odoo Bus signaling.</div>\n                </div>\n            </div>\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_voice_stun_servers" placeholder="stun:stun.l.google.com:19302" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_voice_stun_servers"/>\n                    <div class="text-muted">Comma separated STUN servers.</div>\n                </div>\n            </div>\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_voice_turn_servers" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_voice_turn_servers"/>\n                    <div class="text-muted">JSON list for TURN servers (recommended for NAT traversal).</div>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <div class="app_settings_block o_app" data-key="ai_api" data-string="AI Assistant (API)" string="AI Assistant (API)">\n        <h2>AI Assistant (API)</h2>\n        <div class="row mt16 o_settings_container">\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_api_provider" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_api_provider"/>\n                    <div class="text-muted">Choose your provider or use Custom.</div>\n                </div>\n            </div>\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_api_base_url" placeholder="(use provider default)" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_api_base_url"/>\n                    <div class="text-muted">Optional override. Example (Groq): https://api.groq.com/openai/v1</div>\n                </div>\n            </div>\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_api_key" password="True" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_api_key"/>\n                    <div class="text-muted">Your API key is saved in System Parameters.</div>\n                </div>\n            </div>\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_api_model" placeholder="llama-3.1-70b-versatile / gpt-4o ..." groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_api_model"/>\n                    <div class="text-muted">Default model used by the assistant.</div>\n                </div>\n            </div>\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_api_temperature" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_api_temperature"/>\n                    <div class="text-muted">Higher = more creative, lower = more deterministic.</div>\n                </div>\n            </div>\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_api_max_tokens" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_api_max_tokens"/>\n                    <div class="text-muted">Cap output length.</div>\n                </div>\n            </div>\n            <div class="col-12 col-lg-6 o_setting_box">\n                <div class="o_setting_left_pane">\n                    <field name="ai_api_timeout" groups="base.group_system"/>\n                </div>\n                <div class="o_setting_right_pane">\n                    <label for="ai_api_timeout"/>\n                    <div class="text-muted">HTTP timeout for requests.</div>\n                </div>\n            </div>\n        </div>\n    </div>\n</xpath>\n'
CANDIDATE_XMLIDS = [
    "base.view_res_config_settings",
    "base_setup.view_res_config_settings",
    "base_setup.view_general_configuration",
    "base.res_config_settings_view_form",
]

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    base_view = None
    for xid in CANDIDATE_XMLIDS:
        try:
            base_view = env.ref(xid, raise_if_not_found=True)
            break
        except Exception:
            continue
    if not base_view:
        return

    existing = env['ir.ui.view'].search([
        ('model', '=', 'res.config.settings'),
        ('inherit_id', '=', base_view.id),
        ('key', '=', 'ai_voice.res_config_settings_inherit_dynamic')
    ], limit=1)

    vals = {
        'name': 'AI Voice & API Settings (dynamic)',
        'type': 'form',
        'model': 'res.config.settings',
        'inherit_id': base_view.id,
        'arch': SETTINGS_XPATH,
        'key': 'ai_voice.res_config_settings_inherit_dynamic',
    }
    if existing:
        existing.write(vals)
    else:
        env['ir.ui.view'].create(vals)

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.ui.view'].search([('key', '=', 'ai_voice.res_config_settings_inherit_dynamic')]).unlink()
