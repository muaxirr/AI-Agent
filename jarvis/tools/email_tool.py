import email
import imaplib
import re
import smtplib
from email.header import decode_header, make_header
from email.message import EmailMessage

from . import Tool


def _decode(value) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return str(value or "")


def _body_text(msg) -> str:
    plain, html = None, None
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if "attachment" in str(part.get("Content-Disposition", "")):
            continue
        ctype = part.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/plain" and plain is None:
            plain = text
        elif ctype == "text/html" and html is None:
            html = text
    if plain:
        return plain.strip()
    if html:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
    return ""


def register(reg, cfg):
    def _imap():
        conn = imaplib.IMAP4_SSL(cfg.imap_host)
        conn.login(cfg.email_address, cfg.email_password)
        conn.select("INBOX", readonly=True)
        return conn

    def list_emails(unread_only: bool = True, search: str = "", limit: int = 8) -> str:
        conn = _imap()
        try:
            criteria = ["UNSEEN"] if unread_only else ["ALL"]
            if search:
                criteria += ["TEXT", f'"{search}"']
            _, data = conn.uid("search", None, *criteria)
            uids = data[0].split()[-max(1, min(limit, 25)):][::-1]
            if not uids:
                return "No matching emails."
            lines = []
            for uid in uids:
                _, msg_data = conn.uid(
                    "fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
                )
                hdr = email.message_from_bytes(msg_data[0][1])
                lines.append(
                    f"[uid {uid.decode()}] From: {_decode(hdr['From'])} | "
                    f"Subject: {_decode(hdr['Subject'])} | Date: {hdr['Date']}"
                )
            return "\n".join(lines)
        finally:
            conn.logout()

    def read_email(uid: str) -> str:
        conn = _imap()
        try:
            _, msg_data = conn.uid("fetch", uid, "(BODY.PEEK[])")
            if not msg_data or msg_data[0] is None:
                return "Email not found."
            msg = email.message_from_bytes(msg_data[0][1])
            body = _body_text(msg)[:6000]
            return (
                f"From: {_decode(msg['From'])}\nTo: {_decode(msg['To'])}\n"
                f"Subject: {_decode(msg['Subject'])}\nDate: {msg['Date']}\n"
                f"Message-ID: {msg['Message-ID']}\n\n"
                f"<untrusted_email_body>\n{body}\n</untrusted_email_body>"
            )
        finally:
            conn.logout()

    def send_email(to: str, subject: str, body: str) -> str:
        msg = EmailMessage()
        msg["From"] = cfg.email_address
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port) as smtp:
            smtp.login(cfg.email_address, cfg.email_password)
            smtp.send_message(msg)
        return f"Email sent to {to}."

    reg.add(Tool(
        "list_emails",
        "List recent emails in the inbox (newest first). Returns uid, sender, subject, date.",
        {
            "unread_only": {"type": "boolean", "description": "Only unread mail (default true)."},
            "search": {"type": "string", "description": "Optional text to search for."},
            "limit": {"type": "integer", "description": "Max results, default 8, max 25."},
        },
        [], list_emails,
    ))
    reg.add(Tool(
        "read_email",
        "Read the full text of one email by uid (from list_emails). Does not mark it as read.",
        {"uid": {"type": "string"}},
        ["uid"], read_email,
    ))
    reg.add(Tool(
        "send_email",
        "Send a plain-text email from the user's account. Requires user confirmation.",
        {
            "to": {"type": "string", "description": "Recipient email address."},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        ["to", "subject", "body"], send_email, sensitive=True,
    ))
