from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

import httpx


class SecHttpError(RuntimeError):
    pass


@dataclass(frozen=True)
class SecHttpConfig:
    user_agent: str
    timeout_seconds: float = 15.0
    max_attempts: int = 3
    min_interval_seconds: float = 0.12
    backoff_seconds: float = 0.5

    def __post_init__(self) -> None:
        if not self.user_agent.strip() or "@" not in self.user_agent:
            raise ValueError("SEC User-Agent must identify the application and include a contact email")
        if self.timeout_seconds <= 0 or self.max_attempts < 1 or self.min_interval_seconds < 0 or self.backoff_seconds < 0:
            raise ValueError("invalid SEC HTTP configuration")


class SecHttpClient:
    def __init__(
        self,
        config: SecHttpConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None
        self._client = httpx.Client(
            timeout=config.timeout_seconds,
            transport=transport,
            headers={"User-Agent": config.user_agent, "Accept-Encoding": "gzip, deflate"},
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SecHttpClient":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {"sec.gov", "www.sec.gov", "data.sec.gov"}:
            raise ValueError("SEC HTTP client only permits HTTPS SEC domains")

    def _rate_limit(self) -> None:
        now = self._clock()
        if self._last_request_at is not None:
            remaining = self.config.min_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at = self._clock()

    def get_text(self, url: str) -> str:
        self._validate_url(url)
        last_error: Exception | None = None
        for attempt in range(1, self.config.max_attempts + 1):
            self._rate_limit()
            try:
                response = self._client.get(url)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < self.config.max_attempts:
                    self._sleep(self.config.backoff_seconds * attempt)
                    continue
                raise SecHttpError(f"SEC request failed after {attempt} attempts") from exc

            if response.status_code == 200:
                text = response.text
                if not text.strip():
                    raise SecHttpError("SEC returned an empty response")
                return text

            if response.status_code in {403, 429} or 500 <= response.status_code <= 599:
                last_error = SecHttpError(f"SEC retryable HTTP status {response.status_code}")
                if attempt < self.config.max_attempts:
                    self._sleep(self.config.backoff_seconds * attempt)
                    continue
                raise last_error

            raise SecHttpError(f"SEC HTTP status {response.status_code}")

        raise SecHttpError("SEC request failed") from last_error
