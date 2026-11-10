import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("JARVIS_DATA_DIR", Path.home() / ".jarvis"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str = _env("ANTHROPIC_API_KEY")
    model: str = _env("JARVIS_MODEL", "claude-sonnet-5-5")
    wake_word: str = _env("JARVIS_WAKE_WORD", "jarvis").lower()
    conversation_window: int = int(_env("JARVIS_CONVERSATION_WINDOW", "25"))
    user_name: str = _env("JARVIS_USER_NAME", "Sir")

    email_address: str = _env("EMAIL_ADDRESS")
    email_password: str = _env("EMAIL_APP_PASSWORD")
    imap_host: str = _env("IMAP_HOST", "imap.gmail.com")
    smtp_host: str = _env("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(_env("SMTP_PORT", "465"))

    telegram_api_id: str = _env("TELEGRAM_API_ID")
    telegram_api_hash: str = _env("TELEGRAM_API_HASH")
    telegram_session: str = str(DATA_DIR / "telegram")

    wa_token: str = _env("WHATSAPP_TOKEN")
    wa_phone_id: str = _env("WHATSAPP_PHONE_NUMBER_ID")
    wa_verify_token: str = _env("WHATSAPP_VERIFY_TOKEN")
    wa_app_secret: str = _env("WHATSAPP_APP_SECRET")
    wa_port: int = int(_env("WHATSAPP_WEBHOOK_PORT", "8085"))
    wa_db: str = str(DATA_DIR / "whatsapp.sqlite")


cfg = Config()
