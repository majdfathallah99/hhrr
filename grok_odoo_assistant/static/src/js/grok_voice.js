/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";

(function () {
    function appendMessage(role, text) {
        const ul = document.getElementById("grok_messages");
        if (!ul) return;
        const li = document.createElement("li");
        li.textContent = role.toUpperCase() + ": " + text;
        ul.appendChild(li);
        ul.scrollTop = ul.scrollHeight;
    }

    async function sendToServer(message, execute) {
        const sessionId = document.getElementById("grok_session_id")?.value || "";
        const payload = {
            session_id: sessionId,
            message: message,
            execute: !!execute,
        };
        try {
            const res = await jsonrpc("/grok/chat", payload);
            return res;
        } catch (e) {
            console.error("RPC error", e);
            return { reply: "RPC error: " + (e && e.message ? e.message : e), results: [] };
        }
    }

    function speak(text) {
        if (!window.speechSynthesis) return;
        const utter = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utter);
    }

    function setupUI() {
        const btn = document.getElementById("grok_send");
        const inp = document.getElementById("grok_text");
        const chk = document.getElementById("grok_execute");
        const startBtn = document.getElementById("grok_start_stop");

        if (btn && inp) {
            btn.addEventListener("click", async () => {
                const msg = inp.value.trim();
                if (!msg) return;
                appendMessage("user", msg);
                inp.value = "";
                const res = await sendToServer(msg, chk && chk.checked);
                appendMessage("assistant", res.reply || "");
                if (res.results && res.results.length) {
                    appendMessage("assistant", "Actions: " + res.results.join(" | "));
                }
                speak(res.reply || "");
            });
            inp.addEventListener("keydown", (ev) => {
                if (ev.key === "Enter") btn.click();
            });
        }

        let recognizing = false;
        let recognition = null;
        if (window.SpeechRecognition || window.webkitSpeechRecognition) {
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SR();
            recognition.lang = "en-US";
            recognition.continuous = true;
            recognition.interimResults = false;

            recognition.onresult = async (event) => {
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        const transcript = event.results[i][0].transcript;
                        appendMessage("user", transcript);
                        const res = await sendToServer(transcript, chk && chk.checked);
                        appendMessage("assistant", res.reply || "");
                        if (res.results && res.results.length) {
                            appendMessage("assistant", "Actions: " + res.results.join(" | "));
                        }
                        speak(res.reply || "");
                    }
                }
            };
            recognition.onerror = (e) => {
                console.warn("Speech recognition error", e);
            };
        }

        if (startBtn) {
            startBtn.addEventListener("click", () => {
                if (!recognition) {
                    alert("SpeechRecognition not supported in this browser.");
                    return;
                }
                if (!recognizing) {
                    recognition.start();
                    recognizing = true;
                    startBtn.textContent = "Stop Voice";
                } else {
                    recognition.stop();
                    recognizing = false;
                    startBtn.textContent = "Start Voice";
                }
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupUI);
    } else {
        setupUI();
    }
})();