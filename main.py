"""JARVIS entry point.

    python main.py                  # voice mode (wake word: "Jarvis")
    python main.py --text           # type instead of speak (no microphone needed)
    python main.py --login-telegram # one-time Telegram login
"""
import argparse
import time

from jarvis.brain import Brain
from jarvis.config import cfg
from jarvis.tools import build_registry

EXIT_PHRASES = ("goodbye", "shut down", "power down", "go to sleep")


def confirm_text(summary: str) -> bool:
    return input(f"\n⚠  Confirm action: {summary}\n   Proceed? [y/N] ").strip().lower() in ("y", "yes")


def start_services() -> None:
    if cfg.wa_token and cfg.wa_phone_id and cfg.wa_verify_token:
        from jarvis.tools.whatsapp_tool import start_webhook

        start_webhook(cfg)
        print(f"WhatsApp webhook listening on port {cfg.wa_port} (path /webhook).")


def run_text(brain: Brain) -> None:
    print("JARVIS online (text mode). Type 'exit' to quit.")
    while True:
        try:
            text = input("\nYOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("exit", "quit"):
            break
        print(f"JARVIS: {brain.respond(text)}")


def run_voice(brain: Brain, voice) -> None:
    voice.speak(f"All systems online. Say {cfg.wake_word} when you need me, {cfg.user_name}.")
    active_until = 0.0
    while True:
        heard = voice.listen()
        if not heard:
            continue
        low = heard.lower()
        if cfg.wake_word in low:
            command = heard[low.index(cfg.wake_word) + len(cfg.wake_word):].strip(" ,.!?")
        elif time.time() < active_until:
            command = heard
        else:
            continue
        if not command:
            voice.speak("Yes?")
            active_until = time.time() + cfg.conversation_window
            continue
        if any(p in command.lower() for p in EXIT_PHRASES):
            voice.speak("Goodbye. Powering down.")
            return
        try:
            reply = brain.respond(command)
        except Exception as exc:
            reply = f"I ran into a problem: {exc}"
        voice.speak(reply)
        active_until = time.time() + cfg.conversation_window


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS personal assistant")
    parser.add_argument("--text", action="store_true", help="text mode instead of voice")
    parser.add_argument("--login-telegram", action="store_true", help="one-time Telegram login")
    args = parser.parse_args()

    if args.login_telegram:
        from jarvis.tools.telegram_tool import login

        login(cfg)
        return

    voice = None
    if not args.text:
        from jarvis.voice import Voice

        voice = Voice()

    registry = build_registry(voice.confirm if voice else confirm_text)
    print(f"Loaded {len(registry)} tools.")
    start_services()
    brain = Brain(registry)

    if voice:
        run_voice(brain, voice)
    else:
        run_text(brain)


if __name__ == "__main__":
    main()
