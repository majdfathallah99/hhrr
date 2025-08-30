/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onMounted, useState } from "@odoo/owl";

export class VoiceDialog extends Component {
    static template = "ai_voice.VoiceDialog";
    setup() {
        this.state = useState({
            status: "Click 'Talk' and speak…",
            transcript: "",
            reply: "",
            listening: false,
        });
        this._recognition = null;
        this._hasSpeech = "webkitSpeechRecognition" in window || "SpeechRecognition" in window;
    }
    close() {
        this.toggleListen(false);
        this.el.closest(".o_dialog_container")?.remove();
    }
    _ensureRecognition() {
        if (!this._hasSpeech) {
            this.state.status = "SpeechRecognition not available in this browser.";
            return null;
        }
        if (this._recognition) return this._recognition;
        const Cls = window.SpeechRecognition || window.webkitSpeechRecognition;
        const rec = new Cls();
        rec.lang = document.documentElement.lang || "en-US";
        rec.interimResults = true;
        rec.continuous = true;
        rec.onresult = (e) => {
            let interim = "";
            let finalTxt = "";
            for (let i= e.resultIndex; i < e.results.length; i++) {
                const res = e.results[i];
                const txt = res[0].transcript;
                if (res.isFinal) finalTxt += txt;
                else interim += txt;
            }
            this.state.transcript = (this.state.transcript + " " + finalTxt + " " + interim).trim();
        };
        rec.onerror = (e) => { this.state.status = "Mic error: " + (e.error || "unknown"); };
        rec.onend = () => { this.state.listening = false; this.state.status = "Stopped."; };
        this._recognition = rec;
        return rec;
    }
    toggleListen(force) {
        const want = typeof force === "boolean" ? force : !this.state.listening;
        const rec = this._ensureRecognition();
        if (!rec) return;
        if (want) {
            this.state.status = "Listening… (speak now)";
            try { rec.start(); this.state.listening = true; } catch {}
        } else {
            try { rec.stop(); } catch {}
            this.state.listening = false;
            this.state.status = "Stopped.";
        }
    }
    async sendNow() {
        const text = (this.state.transcript || "").trim();
        if (!text) { this.state.status = "Nothing to send."; return; }
        this.state.status = "Thinking…";
        try {
            const resp = await fetch("/ai_voice/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ jsonrpc: "2.0", params: { text } }),
            });
            const data = await resp.json();
            const reply = data?.result?.reply || "(no reply)";
            this.state.reply = reply;
            this.speakReply();
            this.state.status = "Done.";
        } catch (e) {
            console.error(e);
            this.state.status = "Server error.";
        }
    }
    speakReply() {
        if (!("speechSynthesis" in window)) return;
        const msg = new SpeechSynthesisUtterance(this.state.reply || "");
        try { window.speechSynthesis.cancel(); } catch {}
        window.speechSynthesis.speak(msg);
    }
}

class SystrayVoiceButton extends Component {
    static template = "ai_voice.SystrayVoiceButton";
    setup() {
        this.state = useState({ listening: false });
        onMounted(() => {});
    }
    onClick() {
        const container = document.createElement("div");
        container.className = "o_dialog_container";
        document.body.appendChild(container);
        const dialog = new VoiceDialog(null);
        dialog.mount(container);
    }
}

registry.category("systray").add("ai_voice_systray", {
    Component: SystrayVoiceButton,
});
