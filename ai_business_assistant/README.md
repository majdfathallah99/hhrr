
# AI Business Assistant (Voice + Analytics)

Ask natural language questions about your Odoo data (sales, profit, stock, AR, etc.).
- Uses function-calling: the model selects a tool (safe, whitelisted ORM queries).
- Optional *voice* UI using the browser's Web Speech API (Chrome/Edge).

## Install
1. Copy this addon to your Odoo `addons` path.
2. Update Apps list and install **AI Business Assistant (Voice + Analytics)**.
3. Go to **Settings → AI Business Assistant** and set:
   - Provider, Model (e.g., `gpt-4o-mini`), API key, Base URL if needed.
4. Open `/ai_assistant` and start chatting.

## Notes
- Profit uses Income and Expense accounts from posted entries in the selected range.
- Top selling products uses confirmed/done Sale Orders.
- All tool queries are executed server-side via ORM; no raw SQL.
- Extend by adding new tool_* methods in `models/ai_tools.py` and updating `tool_schemas()`.
