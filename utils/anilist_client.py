"""AniList GraphQL transport + generic HTTP base.

`HttpClient` is a thin aiohttp-style wrapper with bounded 429 retry —
subclass it for other sites. `AniListClient` adds `.query()` for
GraphQL: POSTs to graphql.anilist.co, unwraps `data` / `errors`, and
raises a typed `AniListError` on hard failure. Domain logic (search,
embeds, watch-order walks, trend aggregation) lives on the classes in
`utils.anilist`.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from utils.errors import AniListError, TransportError

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, session) -> None:
        self._session = session

    @property
    def session(self):
        return self._session

    async def request(
        self,
        method: str,
        url: str,
        *,
        cache_ttl: Optional[int] = None,
        **kwargs: Any,
    ):
        """Issue a request and return the `ClientResponse`.

        One bounded retry on HTTP 429 when Retry-After <= 5s; raises
        `TransportError` on network error, non-OK status, or when the
        retry budget is exhausted.
        """
        if cache_ttl is not None:
            kwargs["expire_after"] = cache_ttl

        for attempt in range(3):
            try:
                resp = await self._session.request(method, url, **kwargs)
            except Exception as e:
                raise TransportError(f"{method} {url} failed: {e}") from e

            if resp.ok:
                return resp

            if resp.status == 429 and attempt < 2:
                retry_after_raw = resp.headers.get("Retry-After", 1.0)
                try:
                    retry_after = float(retry_after_raw)
                except (ValueError, TypeError):
                    retry_after = 1.0

                if retry_after <= 300:
                    logger.info(f"{method} {url} -> 429; retrying after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                raise TransportError(
                    f"{method} {url} rate limited (Retry-After={retry_after})"
                )

            raise TransportError(f"{method} {url} failed with status {resp.status}")

        raise TransportError(f"{method} {url}: retries exhausted")


class AniListClient(HttpClient):
    URL = "https://graphql.anilist.co"

    def __init__(
        self,
        session,
        fallback: Optional[Any] = None,
        cooldown_seconds: float = 120.0,
        failure_threshold: int = 2,
    ) -> None:
        super().__init__(session)
        self.fallback = fallback
        self.cooldown_seconds = cooldown_seconds
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.circuit_open_until = 0.0
        self.is_up = True

    @property
    def is_circuit_open(self) -> bool:
        """Returns True if the circuit breaker is currently OPEN."""
        return time.time() < self.circuit_open_until

    @property
    def is_available(self) -> bool:
        """Returns True if AniList is available (healthy and circuit closed)."""
        return self.is_up and not self.is_circuit_open

    def record_success(self) -> None:
        """Record successful query, resetting circuit breaker."""
        if not self.is_up or self.failure_count > 0 or self.circuit_open_until > 0:
            logger.info("AniList API has recovered; circuit breaker CLOSED; is_up=True")
        self.is_up = True
        self.failure_count = 0
        self.circuit_open_until = 0.0

    def record_failure(self, err: Exception, force_open: bool = False) -> None:
        """Record failure and trip circuit breaker if threshold is exceeded."""
        self.failure_count += 1
        err_str = str(err).lower()
        is_critical = (
            force_open
            or "temporarily disabled" in err_str
            or "status 403" in err_str
            or "status 502" in err_str
            or "status 503" in err_str
            or "status 504" in err_str
        )
        if is_critical or self.failure_count >= self.failure_threshold:
            self.is_up = False
            self.circuit_open_until = time.time() + self.cooldown_seconds
            logger.warning(
                f"AniList API unavailable ({err}); circuit breaker OPEN for {self.cooldown_seconds}s; is_up=False"
            )

    async def check_health(self) -> bool:
        """Probe AniList GraphQL endpoint to verify availability."""
        probe_query = "query { Media(id: 1) { id } }"
        payload: dict[str, Any] = {"query": probe_query}
        try:
            resp = await self._session.request("POST", self.URL, json=payload, timeout=9.9, expire_after=60)
            if not resp.ok:
                self.record_failure(TransportError(f"Health probe returned HTTP {resp.status}"))
                self.is_up = False
                return False

            body = await resp.json()
            if body.get("errors"):
                err_str = str(body["errors"]).lower()
                if "temporarily disabled" in err_str or "maintenance" in err_str:
                    self.record_failure(
                        AniListError(f"Health probe returned outage error: {body['errors']}"),
                        force_open=True,
                    )
                    self.is_up = False
                    return False

            self.record_success()
            return True
        except Exception as e:
            self.record_failure(e)
            self.is_up = False
            return False

    async def query(
        self,
        document: str,
        variables: Optional[dict] = None,
        *,
        cache_ttl: Optional[int] = None,
        partial: bool = False,
    ) -> dict:
        """POST a GraphQL op, return the `data` payload.

        `partial` tolerates errors on some fields (left null) if the rest came back.
        """
        if not self.is_available:
            raise AniListError(
                f"AniList is currently unavailable (is_up={self.is_up}, circuit_open={self.is_circuit_open})"
            )

        payload: dict[str, Any] = {"query": document}
        if variables is not None:
            payload["variables"] = variables

        try:
            resp = await self.request("POST", self.URL, json=payload, cache_ttl=cache_ttl)
        except TransportError as e:
            self.record_failure(e)
            raise AniListError(str(e)) from e

        body = await resp.json()
        if body.get("errors") and partial and any((body.get("data") or {}).values()):
            self.record_success()
            return body["data"]
        if body.get("errors"):
            err_msg = f"AniList GraphQL errors: {body['errors']}"
            err_str = str(body["errors"]).lower()
            if "temporarily disabled" in err_str or "maintenance" in err_str:
                self.record_failure(AniListError(err_msg), force_open=True)
            else:
                self.record_failure(AniListError(err_msg))
            raise AniListError(err_msg)

        self.record_success()
        return body.get("data") or {}


def end_of_day_utc_ttl() -> int:
    """Seconds until end of day UTC. Used for `isBirthday` queries so the
    cached response rolls over when the day does, not 24h after the hit."""
    now = datetime.now(timezone.utc)
    tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
    return int((tomorrow - now).total_seconds())
