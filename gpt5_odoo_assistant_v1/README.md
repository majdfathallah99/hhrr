
# GPT-5 Odoo Assistant (Odoo 17)

An agent-mode AI assistant that talks to OpenAI's API and can (optionally) call *safe* tools to read or modify Odoo data.

> Created 2025-09-03T12:15:18.979727 UTC

## Features
- Chat threads saved in Odoo (per user)
- Calls OpenAI's **Responses API** (with fallback to **Chat Completions**) using `requests`
- Tool calling: `search_read`, `get_model_fields`, `create`, `write`, `unlink`, `run_server_action`
- Per-thread safety gates: *sudo mode*, write/create/unlink toggles, allowed models
- Configurable model, base URL, and API key in **Settings > General Settings > GPT-5 Assistant**
- Security groups: User / Manager / Superuser
- Basic wizard to ask a quick question from anywhere
- Menu: **AI Assistant > Threads**

## Install
1. Copy this folder into your Odoo 17 addons path.
2. Install Python dependency:
   ```bash
   pip install requests
   ```
3. Update Apps and install **GPT-5 Odoo Assistant**.
4. Go to **Settings > General Settings > GPT-5 Assistant** and set:
   - **API Base URL** (default: `https://api.openai.com/v1`)
   - **API Key**
   - **Model** (e.g., `gpt-5` or `gpt-4o-mini`)
5. Open **AI Assistant > Threads**, create a new thread, and chat.

## Notes
- By enabling **Sudo mode** or write access toggles on a thread, you allow the assistant broader access. Keep these off unless you fully trust the operator and the model.
- Allowed models can be restricted per thread. If **Allow all models** is enabled (requires Superuser group), all models are exposed.
- The module aims to be backend-only and lightweight. You can add custom UI in `web.assets_backend` later.

## Uninstall
Just uninstall the module from Apps.
