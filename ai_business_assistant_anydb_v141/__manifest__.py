{
    'name': 'AI Business Assistant ANYDB v140 (with Live Voice Chat)',
    'summary': 'Adds a mic button (ASR+TTS) and a settings menu.',
    'version': '18.0.1.40',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'depends': ['web', 'base'],
    'data': [
        'views/assets.xml',
        'views/res_config_settings_view.xml',
        'security/ir.model.access.csv',
        'data/voice_menu.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'ai_business_assistant_anydb_v140/static/src/scss/voice.scss',
            'ai_business_assistant_anydb_v140/static/src/js/voice_systray.js',
            'ai_business_assistant_anydb_v140/static/src/xml/voice_templates.xml'
        ]
    },
    'installable': True,
    'application': False
}