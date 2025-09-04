# GPT‑5 AI Assistant (Odoo 17/18)

A minimal, secure, OpenAI-compatible chat assistant inside Odoo.

## Install
1. Copy `gpt5_ai_assistant` to your addons path.
2. Ensure server has `openai` package (requirements.txt or pip install openai).
3. Update Apps and install the module.
4. Go to **Settings → GPT‑5 Assistant** and set API Key, Model, optional Base URL, and System Prompt.
5. Open **GPT‑5 Assistant → Chat**.

## Notes
- Works with OpenAI or any OpenAI-compatible endpoint (set Base URL).
- API key stored in `ir.config_parameter` (not in code).
- Extend controller to inject Odoo data context before calling the model.