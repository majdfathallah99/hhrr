import logging, requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an Odoo-savvy voice assistant. Keep answers short and speak-ready. "
    "If the user asks about Odoo data or actions, reply with concise guidance; avoid secrets."
)

def _conf(env):
    ICP = env["ir.config_parameter"].sudo()
    return {
        "enabled": ICP.get_param("ai_voice.enabled", "True") == "True",
        "model": ICP.get_param("ai_voice.model", "llama-3.1-8b-instant"),
        "base_url": (ICP.get_param("ai_voice.base_url", "https://api.groq.com/openai/v1") or "").rstrip("/"),
        "api_key": ICP.get_param("ai_voice.api_key") or "",
    }

class AIVoiceController(http.Controller):

    @http.route("/ai_voice", type="http", auth="user", csrf=False)
    def ui(self, **kw):
        # Simple inlined UI (keeps your original assets untouched)
        html = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>AI Voice Assistant</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;padding:24px;background:#0b1020;color:#e6e8ef}
    .wrap{max-width:960px;margin:0 auto}
    h1{font-size:24px;margin:0 0 8px}
    p.muted{opacity:.7;margin:0 0 16px}
    .panel{background:#0f162f;border:1px solid #1f2b54;border-radius:16px;padding:16px 16px}
    .row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
    .btn{border-radius:999px;border:1px solid #4763c6;background:#1b2a63;color:#fff;padding:14px 18px;cursor:pointer;font-weight:600}
    .btn.secondary{background:#21325f;border-color:#3d4f9c}
    .msglist{list-style:none;margin:16px 0 0;padding:0;max-height:55vh;overflow:auto}
    .msg{padding:12px 14px;border-radius:14px;margin:6px 0;line-height:1.35}
    .me{background:#183365;border:1px solid #274a99}
    .bot{background:#16243e;border:1px solid #2b3f7a}
    .inputrow{display:flex;gap:8px;margin-top:8px}
    input[type=text]{flex:1;min-width:240px;border-radius:12px;border:1px solid #2e3d74;background:#0b1534;color:#fff;padding:12px}
    .pill{font-size:12px;border:1px solid #344a9c;border-radius:999px;padding:6px 10px;margin-left:8px;background:#121a38}
    .status{margin-left:auto;opacity:.8}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>AI Voice Assistant <span id="model" class="pill"></span></h1>
    <p class="muted">Hold the mic button and speak. Browser uses Web Speech API; server calls your OpenAI-compatible endpoint.</p>

    <div class="panel">
      <div class="row">
        <button id="mic" class="btn">🎤 Hold to talk</button>
        <button id="speakToggle" class="btn secondary">🔈 Speak: On</button>
        <span id="status" class="status">Idle</span>
      </div>

      <ul id="messages" class="msglist"></ul>

      <div class="inputrow">
        <input id="text" type="text" placeholder="Type instead…"/>
        <button id="send" class="btn secondary">Send</button>
      </div>
    </div>
  </div>

<script>
const el = (id) => document.getElementById(id);
const messages = el('messages');
const statusEl = el('status');
const speakBtn = el('speakToggle');
const modelPill = el('model');
let speakEnabled = true;

function addMsg(text, who){
  const li = document.createElement('li');
  li.className = 'msg ' + (who === 'me' ? 'me' : 'bot');
  li.textContent = text;
  messages.appendChild(li);
  messages.scrollTop = messages.scrollHeight;
}

function speak(text){
  if(!speakEnabled) return;
  if (!('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

function initSpeechRecognition(){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR){ return null; }
  const r = new SR();
  r.lang = navigator.language || 'en-US';
  r.interimResults = false;
  r.maxAlternatives = 1;
  return r;
}

async function askLLM(text){
  statusEl.textContent = 'Thinking…';
  const res = await fetch('/ai_voice/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: text})
  });
  const data = await res.json();
  statusEl.textContent = 'Idle';
  return data;
}

speakBtn.onclick = () => {
  speakEnabled = !speakEnabled;
  speakBtn.textContent = speakEnabled ? '🔈 Speak: On' : '🔇 Speak: Off';
};

el('send').onclick = async () => {
  const val = el('text').value.trim();
  if(!val) return;
  el('text').value = '';
  addMsg(val, 'me');
  const r = await askLLM(val);
  if(r && r.text){
    addMsg(r.text, 'bot');
    speak(r.text);
  }
};

// Mic hold-to-talk
const mic = el('mic');
const recog = initSpeechRecognition();
if(!recog){
  mic.textContent = '🎤 Speech not supported (use text)';
  mic.disabled = false;
} else {
  mic.onmousedown = () => { statusEl.textContent = 'Listening…'; recog.start(); };
  mic.onmouseup = () => { try{ recog.stop(); }catch(e){} };
  mic.ontouchstart = (e) => { e.preventDefault(); statusEl.textContent = 'Listening…'; recog.start(); };
  mic.ontouchend = (e) => { e.preventDefault(); try{ recog.stop(); }catch(e){} };

  recog.onresult = async (ev) => {
    const txt = ev.results[0][0].transcript;
    addMsg(txt, 'me');
    const r = await askLLM(txt);
    if(r && r.text){
      addMsg(r.text, 'bot');
      speak(r.text);
    }
  };
  recog.onerror = (e) => { statusEl.textContent = 'Mic error: ' + (e.error || 'Unknown'); };
  recog.onend = () => { statusEl.textContent = 'Idle'; };
}

(async () => {
  try{
    const meta = await fetch('/ai_voice/meta').then(r=>r.json());
    modelPill.textContent = meta.model || '';
  }catch(e){}
})();
</script>
</body>
</html>
        """
        return request.make_response(html, headers=[("Content-Type","text/html; charset=utf-8")], status=200)

    @http.route("/ai_voice/meta", type="json", auth="user", csrf=False)
    def meta(self, **kw):
        c = _conf(request.env)
        return {"model": c["model"], "enabled": c["enabled"]}

    @http.route("/ai_voice/chat", type="json", auth="user", methods=["POST"], csrf=False)
    def chat(self, **kw):
        c = _conf(request.env)
        if not c["enabled"]:
            return {"text": "Voice assistant is disabled in settings."}
        msg = (kw or {}).get("message") or ""
        if not msg.strip():
            return {"text": "Say something first."}

        headers = {"Authorization": f"Bearer {c['api_key']}", "Content-Type": "application/json"}
        payload = {
            "model": c["model"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": msg.strip()}
            ],
            "temperature": 0.3,
        }
        try:
            url = f"{c['base_url']}/chat/completions"
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or "..."
            return {"text": text}
        except Exception as e:
            _logger.exception("AI voice error")
            return {"text": "Error contacting AI provider. Check API key/base URL."}