/** @odoo-module **/
import { registry } from "@web/core/registry";

const actionRegistry = registry.category("actions");

actionRegistry.add("ai_assistant.client", (env, options) => {
    return {
        async start() {
            const iframe = document.createElement("iframe");
            iframe.src = "/ai_assistant_minimal";
            iframe.style.border = "0";
            iframe.style.width = "100%";
            iframe.style.height = "calc(100vh - 48px)";
            this.el.appendChild(iframe);
        },
    };
});
