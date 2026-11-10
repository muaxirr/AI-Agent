"""WhatsApp via the official Meta WhatsApp Business Cloud API.

Sending: POST to the Graph API.
Receiving: Meta calls a webhook; we run a small Flask server that stores incoming
messages in SQLite so Jarvis can read them. Expose the port publicly (e.g. with
`ngrok http 8085`) and register the URL + verify token in the Meta developer console.
"""
import hashlib
import hmac
import sqlite3
import threading
import time

import requests

from . import Tool

GRAPH = "https://graph.facebook.com/v21.0"


def _db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, sender TEXT, name TEXT, body TEXT)"
    )
    return conn


def start_webhook(cfg) -> None:
    from flask import Flask, request

    app = Flask("jarvis-whatsapp")
    conn = _db(cfg.wa_db)
    lock = threading.Lock()

    @app.get("/webhook")
    def verify():
        if (
            request.args.get("hub.mode") == "subscribe"
            and request.args.get("hub.verify_token") == cfg.wa_verify_token
        ):
            return request.args.get("hub.challenge", ""), 200
        return "forbidden", 403

    @app.post("/webhook")
    def incoming():
        if cfg.wa_app_secret:
            sig = request.headers.get("X-Hub-Signature-256", "")
            expected = "sha256=" + hmac.new(
                cfg.wa_app_secret.encode(), request.get_data(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return "bad signature", 403
        payload = request.get_json(silent=True) or {}
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                names = {
                    c.get("wa_id"): c.get("profile", {}).get("name", "")
                    for c in value.get("contacts", [])
                }
                for m in value.get("messages", []):
                    body = m.get("text", {}).get("body") or f"<{m.get('type', 'unknown')} message>"
                    with lock:
                        conn.execute(
                            "INSERT INTO messages (ts, sender, name, body) VALUES (?,?,?,?)",
                            (int(m.get("timestamp", time.time())), m.get("from"),
                             names.get(m.get("from"), ""), body),
                        )
                        conn.commit()
        return "ok", 200

    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=cfg.wa_port, use_reloader=False),
        daemon=True,
    ).start()


def register(reg, cfg):
    conn = _db(cfg.wa_db)

    def send(to: str, text: str) -> str:
        number = "".join(ch for ch in to if ch.isdigit())
        resp = requests.post(
            f"{GRAPH}/{cfg.wa_phone_id}/messages",
            headers={"Authorization": f"Bearer {cfg.wa_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": number,
                "type": "text",
                "text": {"body": text},
            },
            timeout=20,
        )
        if resp.status_code >= 400:
            return f"WhatsApp API error {resp.status_code}: {resp.text[:300]}"
        return f"WhatsApp message sent to +{number}."

    def recent(limit: int = 10, sender: str = "") -> str:
        q = "SELECT ts, sender, name, body FROM messages"
        args: tuple = ()
        if sender:
            q += " WHERE sender LIKE ? OR name LIKE ?"
            args = (f"%{sender}%", f"%{sender}%")
        q += " ORDER BY id DESC LIMIT ?"
        rows = conn.execute(q, args + (max(1, min(limit, 30)),)).fetchall()
        if not rows:
            return "No WhatsApp messages received yet."
        lines = [
            f"[{time.strftime('%b %d %H:%M', time.localtime(ts))}] {name or snd} (+{snd}): {body}"
            for ts, snd, name, body in reversed(rows)
        ]
        return "<untrusted_chat_messages>\n" + "\n".join(lines) + "\n</untrusted_chat_messages>"

    reg.add(Tool(
        "whatsapp_recent_messages",
        "Read the most recent incoming WhatsApp messages (received via webhook).",
        {
            "limit": {"type": "integer"},
            "sender": {"type": "string", "description": "Optional name or phone filter."},
        },
        [], recent,
    ))
    reg.add(Tool(
        "whatsapp_send_message",
        "Send a WhatsApp text message. 'to' is a phone number with country code. "
        "Free-form text only works within 24h of the contact's last message. Requires confirmation.",
        {"to": {"type": "string"}, "text": {"type": "string"}},
        ["to", "text"], send, sensitive=True,
    ))
