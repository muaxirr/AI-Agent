"""Tool registry. Every capability Jarvis has is a Tool registered here.

Tools flagged ``sensitive`` (sending messages, running shell commands,
typing on the keyboard...) require explicit user confirmation before they run.
"""
import json
from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    properties: dict
    required: list
    fn: Callable[..., str]
    sensitive: bool = False


class Registry:
    def __init__(self, confirm: Callable[[str], bool]):
        self._tools: dict[str, Tool] = {}
        self._confirm = confirm

    def add(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def __len__(self) -> int:
        return len(self._tools)

    def schemas(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": {
                    "type": "object",
                    "properties": t.properties,
                    "required": t.required,
                },
            }
            for t in self._tools.values()
        ]

    def call(self, name: str, args: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'."
        if tool.sensitive:
            summary = f"{name} {json.dumps(args, ensure_ascii=False)[:400]}"
            if not self._confirm(summary):
                return "The user declined this action. Do not retry it."
        try:
            return str(tool.fn(**args))
        except Exception as exc:  # surface errors to the model so it can recover
            return f"Error running {name}: {type(exc).__name__}: {exc}"


def build_registry(confirm) -> Registry:
    from ..config import cfg
    from . import email_tool, system_tool, telegram_tool, whatsapp_tool

    reg = Registry(confirm)
    system_tool.register(reg, cfg)
    if cfg.email_address and cfg.email_password:
        email_tool.register(reg, cfg)
    if cfg.telegram_api_id and cfg.telegram_api_hash:
        telegram_tool.register(reg, cfg)
    if cfg.wa_token and cfg.wa_phone_id:
        whatsapp_tool.register(reg, cfg)
    return reg
