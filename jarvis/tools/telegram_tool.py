"""Telegram via Telethon (acts as the user's own account, not a bot).

One-time login:  python main.py --login-telegram
"""
import asyncio
import threading

from . import Tool


def login(cfg) -> None:
    """Interactive first-time login (asks for phone number and the code Telegram sends)."""
    from telethon import TelegramClient

    client = TelegramClient(cfg.telegram_session, int(cfg.telegram_api_id), cfg.telegram_api_hash)
    client.start()
    me = client.loop.run_until_complete(client.get_me())
    print(f"Logged in to Telegram as {me.first_name}. Session saved.")
    client.disconnect()


class _TelegramRunner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self._client = None

    def run(self, coro, timeout: int = 60):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    async def client(self):
        if self._client is None:
            from telethon import TelegramClient

            c = TelegramClient(
                self.cfg.telegram_session, int(self.cfg.telegram_api_id), self.cfg.telegram_api_hash
            )
            await c.connect()
            if not await c.is_user_authorized():
                raise RuntimeError("Telegram is not logged in. Run: python main.py --login-telegram")
            self._client = c
        return self._client

    async def find_chat(self, name: str):
        c = await self.client()
        if name.lstrip("-").isdigit() or name.startswith("@") or name.startswith("+"):
            return await c.get_entity(name if not name.lstrip("-").isdigit() else int(name))
        needle = name.lower()
        async for d in c.iter_dialogs(limit=300):
            if needle in (d.name or "").lower():
                return d.entity
        raise ValueError(f"No Telegram chat matching '{name}'.")


def register(reg, cfg):
    tg = _TelegramRunner(cfg)

    def list_chats(limit: int = 10, unread_only: bool = False) -> str:
        async def go():
            c = await tg.client()
            rows = []
            async for d in c.iter_dialogs(limit=100):
                if unread_only and not d.unread_count:
                    continue
                rows.append(f"{d.name} (unread: {d.unread_count})")
                if len(rows) >= limit:
                    break
            return "\n".join(rows) or "No chats found."

        return tg.run(go())

    def read_messages(chat: str, limit: int = 10) -> str:
        async def go():
            c = await tg.client()
            entity = await tg.find_chat(chat)
            lines = []
            async for m in c.iter_messages(entity, limit=max(1, min(limit, 30))):
                if not m.text:
                    continue
                who = "You" if m.out else (getattr(m.sender, "first_name", None) or chat)
                lines.append(f"[{m.date:%b %d %H:%M}] {who}: {m.text}")
            body = "\n".join(reversed(lines)) or "No text messages."
            return f"<untrusted_chat_messages>\n{body}\n</untrusted_chat_messages>"

        return tg.run(go())

    def send_message(chat: str, text: str) -> str:
        async def go():
            c = await tg.client()
            entity = await tg.find_chat(chat)
            await c.send_message(entity, text)
            return f"Telegram message sent to {chat}."

        return tg.run(go())

    reg.add(Tool(
        "telegram_list_chats",
        "List the user's Telegram chats with unread counts.",
        {
            "limit": {"type": "integer"},
            "unread_only": {"type": "boolean"},
        },
        [], list_chats,
    ))
    reg.add(Tool(
        "telegram_read_messages",
        "Read recent messages from a Telegram chat. 'chat' can be a contact/group name, @username or phone.",
        {"chat": {"type": "string"}, "limit": {"type": "integer"}},
        ["chat"], read_messages,
    ))
    reg.add(Tool(
        "telegram_send_message",
        "Send a Telegram message as the user. Requires user confirmation.",
        {"chat": {"type": "string"}, "text": {"type": "string"}},
        ["chat", "text"], send_message, sensitive=True,
    ))
