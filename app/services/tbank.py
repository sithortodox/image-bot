import hashlib
import json
import logging
import uuid
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger("payments")


class TBankError(Exception):
    pass


def _flatten_for_token(data: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in data.items():
        if key == "Token":
            continue
        if isinstance(value, (dict, list)):
            continue
        if value is None:
            continue
        result[key] = str(value)
    return result


def generate_token(params: dict[str, Any], password: str) -> str:
    flat = _flatten_for_token(params)
    flat["Password"] = password
    concat = "".join(flat[k] for k in sorted(flat.keys()))
    return hashlib.sha256(concat.encode("utf-8")).hexdigest()


def verify_notification_token(payload: dict[str, Any], password: str) -> bool:
    received = payload.get("Token")
    if not received:
        return False
    expected = generate_token(payload, password)
    return received == expected


class TBankService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _signed_body(self, body: dict[str, Any]) -> dict[str, Any]:
        body = {**body, "TerminalKey": self.settings.tbank_terminal_key}
        body["Token"] = generate_token(body, self.settings.tbank_password)
        return body

    async def init_payment(
        self,
        amount: int,
        order_id: str,
        description: str,
    ) -> dict[str, Any]:
        body = {
            "Amount": amount,
            "OrderId": order_id,
            "Description": description,
            "NotificationURL": self.settings.tbank_notification_url,
            "SuccessURL": self.settings.tbank_success_url,
            "FailURL": self.settings.tbank_fail_url,
        }
        signed = self._signed_body(body)
        url = f"{self.settings.tbank_api_url.rstrip('/')}/Init"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=signed)
            data = response.json()

        if not data.get("Success"):
            logger.error("TBank Init failed: %s", json.dumps(data, ensure_ascii=False))
            raise TBankError(data.get("Message") or data.get("Details") or "Init failed")

        return data

    @staticmethod
    def new_order_id(user_id: int, pack_id: str) -> str:
        return f"u{user_id}-{pack_id}-{uuid.uuid4().hex[:12]}"
