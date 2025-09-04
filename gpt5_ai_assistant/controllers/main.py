
from odoo import http
from odoo.http import request

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class AiAssistantController(http.Controller):

    @http.route("/ai_assistant/chat", type="json", auth="user", methods=["POST"], csrf=False)
    def chat(self, prompt=None, history=None):
        """Forward prompt to an OpenAI-compatible API and return the assistant reply.
        Reads configuration from system parameters:
        - ai_assistant.api_key
        - ai_assistant.model (default: 'gpt-4o-mini' or any chat model)
        - ai_assistant.base_url (optional; set this if using a local/OpenRouter/OpenAI-compatible endpoint)
        - ai_assistant.system_prompt (optional; extra instructions)
        """
        if not prompt:
            return {"ok": False, "error": "No prompt provided."}

        icp = request.env["ir.config_parameter"].sudo()
        api_key = (icp.get_param("ai_assistant.api_key", default="") or "").strip()
        model = (icp.get_param("ai_assistant.model", default="gpt-4o-mini") or "").strip()
        base_url = (icp.get_param("ai_assistant.base_url", default="") or "").strip()
        system_prompt = (icp.get_param("ai_assistant.system_prompt", default="You are a helpful AI assistant inside Odoo. Answer succinctly and can reference Odoo data when asked.") or "").strip()

        if not api_key:
            return {"ok": False, "error": "API key is not set. Go to Settings > GPT‑5 Assistant to configure it."}

        if OpenAI is None:
            return {"ok": False, "error": "Python package 'openai' not installed on the server. Add 'openai' to requirements.txt and restart."}

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if isinstance(history, list):
            for m in history[-10:]:
                if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content"):
                    messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": prompt})

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
            )
            content = (resp.choices[0].message.content or "").strip()
            return {"ok": True, "reply": content}
        except Exception as e:
            return {"ok": False, "error": str(e)}
