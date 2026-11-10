# JARVIS: voice-driven personal AI assistant (Python)

Claude is the brain. Python tools give it hands: email, Telegram, WhatsApp, and laptop control.
Say "Jarvis, ..." and it acts. Anything that sends a message or touches your machine in a risky way
asks you to confirm out loud first.

## Layout

```
main.py                     entry point (voice / text / telegram login)
jarvis/brain.py             Claude tool-use loop + conversation memory
jarvis/voice.py             microphone -> text, text -> speech, spoken confirmations
jarvis/config.py            settings from .env
jarvis/tools/email_tool.py      read / search / send (IMAP + SMTP)
jarvis/tools/telegram_tool.py   list / read / send as your own account (Telethon)
jarvis/tools/whatsapp_tool.py   send + receive (official WhatsApp Cloud API)
jarvis/tools/system_tool.py     apps, URLs, volume, media, screenshot, keyboard, files, shell
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then fill it in
```

PyAudio needs PortAudio: `brew install portaudio` (macOS) or `sudo apt install portaudio19-dev` (Linux).
On Windows `pip install pyaudio` works directly.

Run `python main.py --text` first to test without a microphone, then `python main.py` for voice.

### Email
Gmail: turn on 2-step verification, create an App Password
(Google Account > Security > App passwords), put it in `EMAIL_APP_PASSWORD`.

### Telegram
1. Get `api_id` / `api_hash` at https://my.telegram.org (API development tools).
2. Put them in `.env`, then run `python main.py --login-telegram` once (enter phone number and the code).

### WhatsApp
Uses Meta's official Cloud API (not an unofficial scraper, which risks getting your number banned).
1. Create an app at https://developers.facebook.com, add the WhatsApp product, get a token and phone number ID.
2. Run Jarvis, then expose the webhook: `ngrok http 8085`.
3. In the Meta console set the callback URL to `https://<ngrok-host>/webhook` with your `WHATSAPP_VERIFY_TOKEN`,
   and subscribe to the `messages` field.

Limits to know: the API sends from a WhatsApp Business number (not your personal one), you can only read
messages sent to that number, and free-form replies work only within 24h of the contact's last message.

## Safety design

- Sensitive tools (`send_email`, `telegram_send_message`, `whatsapp_send_message`, `run_shell_command`,
  `type_text`, `press_hotkey`) always ask for confirmation. Declining is final for that request.
- Content from emails, chats and files is wrapped as untrusted data and the model is told never to obey
  instructions inside it (protects against prompt injection via a malicious email or message).
- File tools are limited to your home folder.
- Secrets live only in `.env`. Do not commit it.

## Extending

Add a module in `jarvis/tools/`, define a `register(reg, cfg)` function that calls
`reg.add(Tool(name, description, properties, required, fn, sensitive=...))`, and call it from
`build_registry` in `jarvis/tools/__init__.py`. Ideas: calendar, smart home, Spotify, note-taking,
wake-word engine (Porcupine) for always-on listening, offline speech-to-text (faster-whisper).
