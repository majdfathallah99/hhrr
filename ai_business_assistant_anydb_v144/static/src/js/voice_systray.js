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
        this._hasSpeech = ("webkitSpeechRecognition" in window) || ("SpeechRecognition" in window);
    }
    _closest(el, selector) {
        while (el && el.nodeType === 1) {
            if (el.matches(selector)) return el;
            el = el.parentElement;
        }
        return null;
    }
    close() {
        this.toggleListen(false);
        var container = this._closest(this.el, ".o_dialog_container");
        if (container && container.parentNode) {
            container.parentNode.removeChild(container);
        }
    }
    _ensureRecognition() {
        if (!this._hasSpeech) {
            this.state.status = "SpeechRecognition not available in this browser.";
            return null;
        }
        if (this._recognition) return this._recognition;
        var Cls = window.SpeechRecognition || window.webkitSpeechRecognition;
        var rec = new Cls();
        rec.lang = document.documentElement.lang || "en-US";
        rec.interimResults = true;
        rec.continuous = true;
        var self = this;
        rec.onresult = function(e) {
            var interim = "";
            var finalTxt = "";
            for (var i= e.resultIndex; i < e.results.length; i++) {
                var res = e.results[i];
                var txt = res[0].transcript;
                if (res.isFinal) finalTxt += txt;
                else interim += txt;
            }
            self.state.transcript = (self.state.transcript + " " + finalTxt + " " + interim).trim();
        };
        rec.onerror = function(e) { self.state.status = "Mic error: " + (e.error || "unknown"); };
        rec.onend = function() { self.state.listening = false; self.state.status = "Stopped."; };
        this._recognition = rec;
        return rec;
    }
    toggleListen(force) {
        var want = (typeof force === "boolean") ? force : !this.state.listening;
        var rec = this._ensureRecognition();
        if (!rec) return;
        if (want) {
            this.state.status = "Listening… (speak now)";
            try { rec.start(); this.state.listening = true; } catch(e) {}
        } else {
            try { rec.stop(); } catch(e) {}
            this.state.listening = false;
            this.state.status = "Stopped.";
        }
    }
    async sendNow() {
        var text = (this.state.transcript || "").trim();
        if (!text) { this.state.status = "Nothing to send."; return; }
        this.state.status = "Thinking…";
        try {
            const resp = await fetch("/ai_voice/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ jsonrpc: "2.0", params: { text: text } }),
            });
            const data = await resp.json();
            const reply = (data && data.result && data.result.reply) ? data.result.reply : "(no reply)";
            this.state.reply = reply;
            if ("speechSynthesis" in window) {
                var msg = new SpeechSynthesisUtterance(this.state.reply || "");
                try { window.speechSynthesis.cancel(); } catch(e) {}
                window.speechSynthesis.speak(msg);
            }
            this.state.status = "Done.";
        } catch (e) {
            console.error(e);
            this.state.status = "Server error.";
        }
    }
}

class SystrayVoiceButton extends Component {
    static template = "ai_voice.SystrayVoiceButton";
    setup() {
        this.state = useState({ listening: false });
        onMounted(() => {});
    }
    onClick() {
        var container = document.createElement("div");
        container.className = "o_dialog_container";
        document.body.appendChild(container);
        var dialog = new VoiceDialog(null);
        dialog.mount(container);
    }
}

registry.category("systray").add("ai_voice_systray", { Component: SystrayVoiceButton });
