import base64
import logging
import re
from pathlib import Path

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger("app")

DATA_URL_RE = re.compile(
    r"data:image/[\w+.-]+;base64,([A-Za-z0-9+/=\s]+)",
    re.IGNORECASE,
)
HTTP_IMAGE_RE = re.compile(r"https?://\S+\.(?:png|jpg|jpeg|webp)(?:\?\S*)?", re.IGNORECASE)


class OpenRouterError(Exception):
    pass


class OpenRouterService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _mime_for_path(self, path: Path) -> str:
        ext = path.suffix.lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "image/jpeg")

    def _encode_image(self, path: Path) -> str:
        data = path.read_bytes()
        mime = self._mime_for_path(path)
        b64 = base64.standard_b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"

    async def _request_model(self, model: str, image_data_url: str) -> bytes:
        url = f"{self.settings.openrouter_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/image-bot",
            "X-Title": "Image Telegram Bot",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.settings.openrouter_prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
        }
        timeout = httpx.Timeout(self.settings.openrouter_timeout_sec)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                raise OpenRouterError(
                    f"HTTP {response.status_code}: {response.text[:500]}"
                )
            data = response.json()

        return self._extract_image_bytes(data)

    def _extract_image_bytes(self, data: dict) -> bytes:
        choices = data.get("choices") or []
        if not choices:
            raise OpenRouterError("Пустой ответ OpenRouter")

        message = choices[0].get("message") or {}

        for img in message.get("images") or []:
            url = (img.get("image_url") or {}).get("url") or img.get("url")
            if url:
                parsed = self._parse_image_url(url)
                if parsed:
                    return parsed

        content = message.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "image_url":
                        url = (part.get("image_url") or {}).get("url")
                        if url:
                            parsed = self._parse_image_url(url)
                            if parsed:
                                return parsed
                    elif part.get("type") == "text":
                        parts.append(part.get("text") or "")
            content = "\n".join(parts)

        if isinstance(content, str):
            parsed = self._parse_image_url(content)
            if parsed:
                return parsed

        raise OpenRouterError("Модель не вернула изображение")

    def _parse_image_url(self, value: str) -> bytes | None:
        value = value.strip()
        match = DATA_URL_RE.search(value)
        if match:
            return base64.standard_b64decode(match.group(1).replace("\n", ""))
        match = HTTP_IMAGE_RE.search(value)
        if match:
            return None  # handled async in caller if needed
        if value.startswith("data:image/") and ";base64," in value:
            _, b64 = value.split(";base64,", 1)
            return base64.standard_b64decode(b64)
        return None

    async def _download_url(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    async def process_image(self, input_path: Path, output_path: Path) -> str:
        image_data_url = self._encode_image(input_path)
        models = [
            self.settings.openrouter_model,
            self.settings.openrouter_fallback_model,
        ]
        last_error: Exception | None = None

        for model in models:
            if not model:
                continue
            try:
                logger.info("OpenRouter request model=%s", model)
                image_bytes = await self._request_model(model, image_data_url)
                if not image_bytes:
                    raise OpenRouterError("Пустые данные изображения")
                output_path.write_bytes(image_bytes)
                return model
            except OpenRouterError as exc:
                last_error = exc
                logger.warning("OpenRouter model %s failed: %s", model, exc)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("OpenRouter HTTP error model %s: %s", model, exc)

        raise OpenRouterError(str(last_error or "Не удалось обработать изображение"))
