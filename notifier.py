"""Telegram notification transport."""

from __future__ import annotations

import os

import requests
from loguru import logger

TELEGRAM_TIMEOUT = 5
RETRYABLE_HTTP_STATUSES = {408, 425, 429}


class TelegramError(Exception):
    """A message could not be delivered to Telegram."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = True,
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after = retry_after


def _redact(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "<hidden>")


class TelegramNotifier:
    def __init__(
        self,
        bot_key: str,
        chat_id: str,
        *,
        timeout: int = TELEGRAM_TIMEOUT,
        session: requests.Session | None = None,
    ):
        self._bot_key = bot_key
        self._chat_id = chat_id
        self._timeout = timeout
        self._session = session if session is not None else requests.Session()

    def send(self, message: str) -> None:
        """Send a message. Raises TelegramError if it isn't delivered."""
        url = f"https://api.telegram.org/bot{self._bot_key}/sendMessage"

        try:
            response = self._session.post(
                url,
                json={"chat_id": self._chat_id, "text": message},
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as error:
            # The request URL contains the bot token.
            raise TelegramError(_redact(str(error), self._bot_key)) from None

        payload, valid_json = self._parse_payload(response)

        if response.status_code == 200:
            if payload.get("ok") is True:
                return

            description = payload.get("description", "unexpected response")
            raise TelegramError(
                _redact(f"API error [200]: {description}", self._bot_key),
                status_code=200,
                retryable=not valid_json,
            )

        error_code = payload.get("error_code", response.status_code)
        description = payload.get("description") or response.text or "no description"
        retry_after = self._retry_after(payload)
        retryable = (
            response.status_code in RETRYABLE_HTTP_STATUSES
            or response.status_code >= 500
        )

        raise TelegramError(
            _redact(f"API error [{error_code}]: {description}", self._bot_key),
            status_code=response.status_code,
            retryable=retryable,
            retry_after=retry_after,
        )

    @staticmethod
    def _parse_payload(response: requests.Response) -> tuple[dict, bool]:
        try:
            payload = response.json()
        except ValueError:
            return {}, False
        if isinstance(payload, dict):
            return payload, True
        return {}, False

    @staticmethod
    def _retry_after(payload: dict) -> int | None:
        parameters = payload.get("parameters")
        if not isinstance(parameters, dict):
            return None

        raw = parameters.get("retry_after")
        if isinstance(raw, (int, float)):
            return int(raw)
        return None


def send_telegram_message(
    message: str,
    *,
    bot_key: str,
    chat_id: str,
    timeout: int = TELEGRAM_TIMEOUT,
) -> None:
    """Convenience wrapper used by the standalone connection test."""
    TelegramNotifier(bot_key, chat_id, timeout=timeout).send(message)


def _main() -> int:
    from dotenv import load_dotenv

    from logger_config import setup_logger

    load_dotenv()
    setup_logger()

    bot_key = os.getenv("BOT_KEY", "").strip()
    chat_id = os.getenv("CHAT_ID", "").strip()

    if not bot_key or not chat_id:
        logger.error("BOT_KEY and CHAT_ID must be set")
        return 1

    logger.info("Sending test message to Telegram...")
    try:
        TelegramNotifier(bot_key, chat_id).send(
            "✅ Test message from notifier.py — connection is working!"
        )
    except TelegramError as error:
        logger.error("Failed to send the test message: {}", error)
        return 1

    logger.success("Success! Check your Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
