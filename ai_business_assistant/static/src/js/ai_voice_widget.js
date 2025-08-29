
odoo.define('ai_business_assistant.voice_widget', function (require) {
    'use strict';
    const ajax = require('web.ajax');

    function appendLog(text, who) {
        const log = document.getElementById('chat-log');
        const el = document.createElement('div');
        el.style.margin = '6px 0';
        el.innerHTML = `<strong>${who}:</strong> ${_.escape(text)}`;
        log.appendChild(el);
        log.scrollTop = log.scrollHeight;
    }

    function speak(text) {
        try {
            const u = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(u);
        } catch (e) {}
    }

    function send(message) {
        appendLog(message, 'You');
        ajax.jsonRpc('/ai_assistant/query', 'call', {message}).then(res => {
            if (res && res.text) {
                appendLog(res.text, 'Assistant');
                speak(res.text);
            } else {
                appendLog('No response (check settings / API key).', 'Assistant');
            }
        }).catch(err => {
            appendLog('Error: ' + (err && err.message ? err.message : 'Unknown'), 'Assistant');
        });
    }

    function setupUI() {
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const voiceBtn = document.getElementById('voice-btn');

        sendBtn.addEventListener('click', () => {
            if (input.value.trim()) send(input.value.trim());
            input.value = '';
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && input.value.trim()) {
                send(input.value.trim());
                input.value = '';
            }
        });

        let recognition;
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.lang = 'en-US';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;
        } else {
            voiceBtn.disabled = true;
            voiceBtn.title = 'Web Speech API not supported in this browser';
        }

        let listening = false;
        voiceBtn.addEventListener('mousedown', () => {
            if (!recognition) return;
            listening = true;
            voiceBtn.classList.add('btn-danger');
            recognition.start();
        });
        voiceBtn.addEventListener('mouseup', () => {
            if (!recognition) return;
            listening = false;
            voiceBtn.classList.remove('btn-danger');
            try { recognition.stop(); } catch (e) {}
        });
        voiceBtn.addEventListener('mouseleave', () => {
            if (!recognition) return;
            if (listening) {
                listening = false;
                voiceBtn.classList.remove('btn-danger');
                try { recognition.stop(); } catch (e) {}
            }
        });

        if (recognition) {
            recognition.addEventListener('result', (e) => {
                const transcript = e.results[0][0].transcript;
                document.getElementById('chat-input').value = transcript;
                send(transcript);
            });
            recognition.addEventListener('error', (e) => {
                appendLog('Voice error: ' + e.error, 'System');
            });
        }
    }

    document.addEventListener('DOMContentLoaded', setupUI);
});
