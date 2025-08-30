
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const actionRegistry = registry.category("actions");

class VoiceClient extends Component {
    setup() {
        this.bus = useService("bus_service");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.user = useService("user");
        this.state = useState({
            roomKey: "general",
            joined: false,
            peers: {},        // peerId -> RTCPeerConnection
            streams: {},      // peerId -> MediaStream
            myStream: null,
            log: [],
            users: {},
            isMuted: false,
        });
        this.iceServers = [{ urls: ["stun:stun.l.google.com:19302"] }];

        onWillStart(async () => {
            const conf = await this.rpc("/ai_voice/config", {});
            if (!conf.enabled) {
                this.notification.add(_t("Live Voice Chat is disabled in Settings."), { type: "warning" });
            } else if (conf.iceServers) {
                this.iceServers = conf.iceServers;
            }
        });

        onMounted(() => {
            this._onNotification = this._onNotification.bind(this);
            this.bus.addEventListener("notification", this._onNotification);
        });

        onWillUnmount(() => {
            this.bus.removeEventListener("notification", this._onNotification);
            this._leave();
        });
    }

    async openRoom() {
        if (this.state.joined) return;
        if (!navigator.mediaDevices?.getUserMedia) {
            this.notification.add(_t("Your browser does not support audio capture."), { type: "danger" });
            return;
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.state.myStream = stream;
            // Subscribe to bus channel for this room
            const sub = await this.rpc("/ai_voice/subscribe", { room_key: this.state.roomKey });
            if (sub?.channel) {
                this.bus.addChannel(sub.channel);
            }
            this.state.joined = true;
            this._log("Joined room " + this.state.roomKey);
            // Announce presence
            await this._send({ type: "join", uid: this.user.userId, name: this.user.name });
        } catch (e) {
            console.error(e);
            this.notification.add(_t("Microphone permission denied or not available."), { type: "danger" });
        }
    }

    async _send(payload) {
        await this.rpc("/ai_voice/signal", { room_key: this.state.roomKey, payload });
    }

    _onNotification(ev) {
        for (const notif of ev.detail) {
            for (const m of notif) {
                const { channel, message } = m;
                if (!message || message.t !== "ai_voice") continue;
                if (message.room !== this.state.roomKey) continue;
                if (!this.state.joined) continue;
                this._handleSignal(message);
            }
        }
    }

    async _handleSignal(msg) {
        const payload = msg.payload || {};
        const from = msg.sender;
        if (from === this.user.userId) return; // ignore self

        // Keep user map
        if (msg.sender_name) {
            this.state.users[from] = msg.sender_name;
        }

        if (payload.type === "join") {
            // Someone joined, create peer and make an offer
            await this._ensurePeer(from, true);
        } else if (payload.type === "offer") {
            await this._ensurePeer(from, false, payload.sdp);
        } else if (payload.type === "answer") {
            const pc = this.state.peers[from];
            if (pc) {
                await pc.setRemoteDescription(payload.sdp);
            }
        } else if (payload.type === "ice") {
            const pc = this.state.peers[from];
            if (pc) {
                try { await pc.addIceCandidate(payload.candidate); } catch (e) {}
            }
        } else if (payload.type === "leave") {
            this._removePeer(from);
        }
    }

    async _ensurePeer(peerId, isCaller, remoteOffer = null) {
        if (this.state.peers[peerId]) return;
        const pc = new RTCPeerConnection({ iceServers: this.iceServers });
        this.state.peers[peerId] = pc;

        // Local audio
        for (const track of this.state.myStream.getTracks()) {
            pc.addTrack(track, this.state.myStream);
        }

        pc.onicecandidate = (e) => {
            if (e.candidate) {
                this._send({ type: "ice", candidate: e.candidate });
            }
        };
        pc.ontrack = (e) => {
            // first stream
            const stream = e.streams[0];
            this.state.streams[peerId] = stream;
            this.render(true);
        };
        pc.onconnectionstatechange = () => {
            if (["disconnected", "failed", "closed"].includes(pc.connectionState)) {
                this._removePeer(peerId);
            }
        };

        if (isCaller) {
            const offer = await pc.createOffer({ offerToReceiveAudio: true, offerToReceiveVideo: false });
            await pc.setLocalDescription(offer);
            await this._send({ type: "offer", sdp: pc.localDescription });
        } else if (remoteOffer) {
            await pc.setRemoteDescription(remoteOffer);
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            await this._send({ type: "answer", sdp: pc.localDescription });
        }
    }

    _removePeer(peerId) {
        const pc = this.state.peers[peerId];
        if (pc) {
            try { pc.close(); } catch(e){}
        }
        delete this.state.peers[peerId];
        delete this.state.streams[peerId];
        this.render(true);
    }

    toggleMute() {
        if (!this.state.myStream) return;
        const enabled = this.state.myStream.getAudioTracks().every(t => t.enabled);
        for (const t of this.state.myStream.getAudioTracks()) {
            t.enabled = !enabled;
        }
        this.state.isMuted = !enabled;
        this.render(true);
    }

    async _leave() {
        if (!this.state.joined) return;
        await this._send({ type: "leave" });
        // close peers
        for (const k of Object.keys(this.state.peers)) {
            this._removePeer(k);
        }
        // stop local tracks
        if (this.state.myStream) {
            for (const t of this.state.myStream.getTracks()) t.stop();
            this.state.myStream = null;
        }
        this.state.joined = false;
        this.render(true);
    }

    // UI helpers
    _log(msg) { this.state.log.push(msg); this.render(true); }
}

VoiceClient.template = "ai_voice.VoiceClient";

actionRegistry.add("ai_voice_chat_client", (env, action) => {
    return {
        type: "ir.actions.client",
        execute: async () => {
            const root = document.createElement("div");
            root.classList.add("ai-voice-root");
            env.services.ui.block();
            try {
                const comp = new VoiceClient(env, {});
                await comp.mount(root);
                env.services.dialog.add(comp, { title: env._t("Live Voice Chat"), onClose: () => comp._leave() });
            } finally {
                env.services.ui.unblock();
            }
        },
    };
});
