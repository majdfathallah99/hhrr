{
    'name': 'AI Business Assistant – Voice Plus',
    'summary': 'Live voice chat button (ASR + TTS) available from the Odoo systray.',
    'version': '18.0.1.0.0',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'depends': ['web', 'base'],
    'data': [
        'views/assets.xml',
        'views/res_config_settings_view.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_business_assistant_voice_plus/static/src/scss/voice.scss',
            'ai_business_assistant_voice_plus/static/src/js/voice_systray.js',
            'ai_business_assistant_voice_plus/static/src/xml/voice_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
}
