
import json
import requests
from odoo import http
from odoo.http import request

SYSTEM_PROMPT = (
    "You are an Odoo Business Assistant. "
    "Your job is to answer questions about the user's Odoo data. "
    "If a question requires data, call a tool. "
    "Prefer precise numbers with currency where relevant. "
    "Always state the date ranges and company name you used. "
    "If the user asks for years like 'this year', interpret using the server timezone."
)

class AIAssistantController(http.Controller):
    def _provider_config(self):
        ICP = request.env["ir.config_parameter"].sudo()
        return {
            "enabled": ICP.get_param("ai_business_assistant.ai_enabled", "True") == "True",
            "provider": ICP.get_param("ai_business_assistant.ai_provider", "openai"),
            "api_key": ICP.get_param("ai_business_assistant.ai_api_key"),
            "model": ICP.get_param("ai_business_assistant.ai_model", "gpt-4o-mini"),
            "base_url": ICP.get_param("ai_business_assistant.ai_base_url") or "https://api.openai.com/v1",
        }

    def _tool_schemas(self):
        return request.env["ai.business.tools"].sudo().tool_schemas()

    def _chat_completion(self, messages, tools=None):
        cfg = self._provider_config()
        if not cfg.get("enabled"):
            return {"error": "AI Assistant disabled"}
        if cfg["provider"] in ("openai", "azure_openai", "ollama"):
            headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
            url = cfg["base_url"].rstrip("/") + "/chat/completions"
            payload = {"model": cfg["model"], "messages": messages}
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code >= 400:
                return {"error": f"Upstream error {resp.status_code}: {resp.text}"}
            return resp.json()
        return {"error": "Unsupported provider"}

    def _execute_tools_from_response(self, response_json):
        tool_calls_payloads = []
        tool_results_payloads = []
        try:
            choice = response_json.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", []) or []
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name")
                args_raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw)
                except Exception:
                    args = {}
                result = request.env["ai.business.tools"].sudo().execute_tool(name, args)
                tool_calls_payloads.append({"id": tc.get("id"), "name": name, "arguments": args})
                tool_results_payloads.append({"tool_call_id": tc.get("id"), "name": name, "content": result})
            return tool_calls_payloads, tool_results_payloads
        except Exception as e:
            return [], [{"error": str(e)}]

    @http.route("/ai_assistant/query", type="json", auth="user", csrf=False)
    def ai_query(self, message):
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        tools = self._tool_schemas()
        first = self._chat_completion(messages=msgs, tools=tools)
        if first.get("error"):
            return first

        tool_calls, tool_results = self._execute_tools_from_response(first)

        if tool_calls:
            msgs.append(first["choices"][0]["message"])
            for tr in tool_results:
                msgs.append({"role": "tool", "tool_call_id": tr.get("tool_call_id"), "content": json.dumps(tr.get("content"))})
            second = self._chat_completion(messages=msgs, tools=tools)
            final_text = second.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            final_text = first.get("choices", [{}])[0].get("message", {}).get("content", "")

        request.env["ai.assistant.log"].sudo().create({
            "name": message,
            "response_text": final_text,
            "tool_calls_json": json.dumps(tool_calls, ensure_ascii=False),
            "tool_results_json": json.dumps(tool_results, ensure_ascii=False),
        })

        return {"text": final_text, "tool_calls": tool_calls, "tool_results": tool_results}

    @http.route("/ai_assistant", type="http", auth="user", website=True)
    def voice_page(self, **kw):
        values = {}
        return request.render("ai_business_assistant.template_ai_voice_page", values)

@http.route("/ai_assistant_raw", type="http", auth="user")
def voice_page_raw(self, **kw):
    # Minimal HTML page without website assets/layout
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>AI Business Assistant</title>
        <style>
            body { font-family: system-ui, Arial, sans-serif; margin: 24px; }
            .card { border: 1px solid #ddd; border-radius: 10px; padding: 16px; max-width: 900px; }
            #chat-log { height: 260px; overflow: auto; border: 1px solid #e5e5e5; padding: 8px; border-radius: 6px; margin-bottom: 12px; white-space: pre-wrap; }
            .row { display: flex; gap: 8px; }
            input[type=text] { flex: 1; padding: 8px; border-radius: 6px; border: 1px solid #ccc; }
            button { padding: 8px 12px; border-radius: 8px; border: 1px solid #999; cursor: pointer; }
            button.danger { background: #c33; color: #fff; border-color: #a22; }
            small { color: #666; }
        </style>
    </head>
    <body>
        <h1>AI Business Assistant</h1>
        <div class="card">
            <div id="chat-log"></div>
            <div class="row">
                <input id="chat-input" type="text" placeholder="Type your question…"/>
                <button id="send-btn">Send</button>
                <button id="voice-btn">🎤 Hold to talk</button>
            </div>
            <small>Voice uses your browser's Web Speech API (Chrome/Edge). If unsupported, the mic will be disabled.</small>
        </div>
        <script>
            function appendLog(text, who) {
                const log = document.getElementById('chat-log');
                const el = document.createElement('div');
                const strong = document.createElement('strong');
                strong.textContent = who + ': ';
                el.appendChild(strong);
                el.appendChild(document.createTextNode(text));
                el.style.margin = '6px 0';
                log.appendChild(el);
                log.scrollTop = log.scrollHeight;
            }
            function speak(text) {
                try { const u = new SpeechSynthesisUtterance(text); window.speechSynthesis.speak(u); } catch (e) {}
            }
            async function send(message) {
                appendLog(message, 'You');
                try {
                    const res = await fetch('/ai_assistant/query', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        credentials: 'same-origin',
                        body: JSON.stringify({message})
                    });
                    const data = await res.json();
                    if (data && data.text) {
                        appendLog(data.text, 'Assistant');
                        speak(data.text);
                    } else {
                        appendLog('No response (check OpenAI settings / API key).', 'Assistant');
                    }
                } catch (err) {
                    appendLog('Error: ' + (err && err.message ? err.message : 'Unknown'), 'Assistant');
                }
            }
            const input = document.getElementById('chat-input');
            const sendBtn = document.getElementById('send-btn');
            const voiceBtn = document.getElementById('voice-btn');
            sendBtn.addEventListener('click', () => { if (input.value.trim()) send(input.value.trim()); input.value = ''; });
            input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && input.value.trim()) { send(input.value.trim()); input.value=''; }});
            // Voice
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
            voiceBtn.addEventListener('mousedown', () => { if (!recognition) return; listening = true; voiceBtn.classList.add('danger'); recognition.start(); });
            voiceBtn.addEventListener('mouseup', () => { if (!recognition) return; listening = false; voiceBtn.classList.remove('danger'); try { recognition.stop(); } catch (e) {} });
            voiceBtn.addEventListener('mouseleave', () => { if (!recognition) return; if (listening) { listening = false; voiceBtn.classList.remove('danger'); try { recognition.stop(); } catch (e) {} } });
            if (recognition) {
                recognition.addEventListener('result', (e) => { const transcript = e.results[0][0].transcript; input.value = transcript; send(transcript); });
                recognition.addEventListener('error', (e) => { appendLog('Voice error: ' + e.error, 'System'); });
            }
        </script>
    </body>
    </html>
    '''
    return request.make_response(html, headers=[('Content-Type','text/html; charset=utf-8')])
