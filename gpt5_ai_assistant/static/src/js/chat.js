/** @odoo-module **/
import { registry } from "@web/core/registry";
import { onMounted } from "@odoo/owl";

function mountChat(root) {
    const messagesEl = root.querySelector("#gpt5_chat_messages");
    const inputEl = root.querySelector("#gpt5_chat_input");
    const sendBtn = root.querySelector("#gpt5_send_btn");

    const history = [];
    function renderMessage(role, content) {
        const b = document.createElement("div");
        b.className = "gpt5-bubble " + (role === "user" ? "user" : "assistant");
        b.style.margin = "6px 0";
        b.style.padding = "8px 10px";
        b.style.borderRadius = "10px";
        b.style.background = role === "user" ? "#e9f5ff" : "#f6f6f6";
        b.textContent = content;
        messagesEl.appendChild(b);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function send() {
        const text = (inputEl.value || "").trim();
        if (!text) return;
        inputEl.value = "";
        renderMessage("user", text);
        history.push({ role: "user", content: text });

        const result = await fetch("/ai_assistant/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: text, history }),
        }).then(r => r.json()).catch(e => ({ ok: False, error: e?.message || String(e) }));

        if (result?.ok) {
            renderMessage("assistant", result.reply || "(no reply)");
            history.push({ role: "assistant", content: result.reply || "" });
        } else {
            renderMessage("assistant", "⚠ " + (result?.error || "Error"));
        }
    }

    sendBtn.addEventListener("click", send);
    inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter") send();
    });

    renderMessage("assistant", "مرحبًا! أنا مساعد Odoo الذكي. كيف أقدر نساعدك؟ / Hi! I’m your Odoo assistant. How can I help?");
}

const actionRegistry = registry.category("actions");
actionRegistry.add("gpt5_assistant.open_chat", {
    name: "GPT‑5 Assistant",
    setup() {
        onMounted(() => {
            // Create container for our page
            const container = document.createElement("div");
            container.innerHTML = '<t t-call="gpt5_ai_assistant.gpt5_chat_page"/>';
            document.body.appendChild(container);
            // Delay to ensure elements are in the DOM
            setTimeout(() => mountChat(container), 0);
        });
    },
});