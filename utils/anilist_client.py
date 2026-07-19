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

        for attempt in range(2):
            try:
                resp = await self._session.request(method, url, **kwargs)
            except Exception as e:
                raise TransportError(f"{method} {url} failed: {e}") from e

            if resp.ok:
                return resp

            if resp.status == 429 and attempt == 0:
                retry_after_raw = resp.headers.get("Retry-After", 5)
                try:
                    retry_after = float(retry_after_raw)
                except (ValueError, TypeError):
                    retry_after = 5.0

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

    async def query(
        self,
        document: str,
        variables: Optional[dict] = None,
        *,
        cache_ttl: Optional[int] = None,
    ) -> dict:
        """POST a GraphQL op, return the `data` payload."""
        payload: dict[str, Any] = {"query": document}
        if variables is not None:
            payload["variables"] = variables

        try:
            resp = await self.request("POST", self.URL, json=payload, cache_ttl=cache_ttl)
        except TransportError as e:
            raise AniListError(str(e)) from e

        body = await resp.json()
        if body.get("errors"):
            raise AniListError(f"AniList GraphQL errors: {body['errors']}")
        return body.get("data") or {}


def end_of_day_utc_ttl() -> int:
    """Seconds until end of day UTC. Used for `isBirthday` queries so the
    cached response rolls over when the day does, not 24h after the hit."""
    now = datetime.now(timezone.utc)
    tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
    return int((tomorrow - now).total_seconds())
