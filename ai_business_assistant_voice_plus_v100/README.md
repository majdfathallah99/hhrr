# AI Business Assistant – Voice Plus

Adds a **live voice chat button** (like ChatGPT's mic) to the Odoo backend systray.
- Click the mic icon to open an **AI Voice Chat** dialog.
- Speak -> your words are transcribed (Web Speech API) -> on **Send**, the text is posted to `/ai_voice/chat`.
- The server forwards to a configurable endpoint (OpenAI-compatible or your own), or falls back to a demo echo.
- The reply is read aloud with **speechSynthesis** (TTS).

## Configure (optional)
Settings → General Settings → AI Voice Chat
- **Voice Chat Endpoint**: e.g. `https://api.openai.com/v1/chat/completions`
- **API Key** and **Header Name** if required (Authorization Bearer by default)
- Model hint and temperature are passed along if your backend uses them.

## Notes
- Uses browser **Web Speech API** for ASR, supported by Chromium, Edge and Safari. Firefox may lack support.
- No audio is stored on the server. Only transcribed text is sent to the endpoint you configure.
- All code is self-contained; no Odoo Enterprise dependencies.
