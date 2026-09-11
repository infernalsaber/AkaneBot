"""MAL / Jikan v4 REST client for MyAnimeList catalog fallback.

Provides a REST client for the MyAnimeList catalogue, conforming to the Jikan v4
schema. Handles requests, query parameters, optional server key authentication, rate limits,
and error handling.

The API base URL is read from the `MAL_API_BASE_URL` (or `MAL_BASE_URL`)
environment variable by default, falling back to "https://api.jikan.moe/v4".
"""
from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from utils.anilist_client import HttpClient
from utils.errors import MalError, TransportError

logger = logging.getLogger(__name__)


class MalClient(HttpClient):
    DEFAULT_BASE_URL = "https://api.jikan.moe/v4"

    def __init__(
        self,
        session,
        base_url: Optional[str] = None,
        server_key: Optional[str] = None,
    ) -> None:
        super().__init__(session)
        if base_url is None:
            base_url = (
                os.getenv("MAL_API_BASE_URL")
                or os.getenv("MAL_BASE_URL")
                or self.DEFAULT_BASE_URL
            )
        self.base_url = base_url.rstrip("/")

        if server_key is None:
            server_key = os.getenv("MAL_SERVER_KEY")
        self.server_key = server_key

    @property
    def BASE_URL(self) -> str:
        """Backwards compatibility property for BASE_URL."""
        return self.base_url

    def _build_headers(self, headers: Optional[dict] = None) -> dict:
        req_headers = {
            "User-Agent": "AkaneBot/1.0 (+https://github.com/infernalsaber/AkaneBot)",
            "Accept": "application/json",
        }
        if self.server_key:
            req_headers["X-Server-Key"] = self.server_key
        if headers:
            req_headers.update(headers)
        return req_headers

    async def get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        *,
        cache_ttl: Optional[int] = None,
    ) -> Optional[dict]:
        """Send a GET request to MAL/Jikan API and return JSON payload."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        headers = self._build_headers()

        try:
            resp = await self.request(
                "GET",
                url,
                params=clean_params,
                headers=headers,
                cache_ttl=cache_ttl,
            )
            return await resp.json()
        except TransportError as e:
            if "status 404" in str(e):
                logger.debug(f"MAL GET {url} returned 404 (Not Found)")
                return None
            logger.warning(f"MAL request failed: {e}")
            raise MalError(str(e)) from e

    # ---- Anime Endpoints ----

    async def search_anime(
        self, query: str, limit: int = 15, *, cache_ttl: Optional[int] = None
    ) -> List[dict]:
        """Search anime catalogue."""
        data = await self.get(
            "/anime",
            params={"q": query, "limit": limit},
            cache_ttl=cache_ttl,
        )
        if not data or "data" not in data:
            return []
        return data["data"]

    async def get_anime(
        self, mal_id: int, full: bool = True, *, cache_ttl: Optional[int] = None
    ) -> Optional[dict]:
        """Get anime details by MAL ID."""
        path = f"/anime/{mal_id}/full" if full else f"/anime/{mal_id}"
        data = await self.get(path, cache_ttl=cache_ttl)
        if not data or "data" not in data:
            return None
        return data["data"]

    async def get_anime_relations(
        self, mal_id: int, *, cache_ttl: Optional[int] = None
    ) -> List[dict]:
        """Get anime relations (sequels, prequels, side stories, etc.)."""
        data = await self.get(f"/anime/{mal_id}/relations", cache_ttl=cache_ttl)
        if not data or "data" not in data:
            return []
        return data["data"]

    async def get_anime_characters(
        self, mal_id: int, *, cache_ttl: Optional[int] = None
    ) -> List[dict]:
        """Get character appearances for an anime."""
        data = await self.get(f"/anime/{mal_id}/characters", cache_ttl=cache_ttl)
        if not data or "data" not in data:
            return []
        return data["data"]

    # ---- Manga & Light Novel Endpoints ----

    async def search_manga(
        self,
        query: str,
        type_: Optional[str] = None,
        limit: int = 15,
        *,
        cache_ttl: Optional[int] = None,
    ) -> List[dict]:
        """Search manga catalogue. Use type_='lightnovel' for light novels."""
        params: dict[str, Any] = {"q": query, "limit": limit}
        if type_:
            params["type"] = type_
        data = await self.get("/manga", params=params, cache_ttl=cache_ttl)
        if not data or "data" not in data:
            return []
        return data["data"]

    async def get_manga(
        self, mal_id: int, full: bool = True, *, cache_ttl: Optional[int] = None
    ) -> Optional[dict]:
        """Get manga details by MAL ID."""
        path = f"/manga/{mal_id}/full" if full else f"/manga/{mal_id}"
        data = await self.get(path, cache_ttl=cache_ttl)
        if not data or "data" not in data:
            return None
        return data["data"]

    # ---- Character Endpoints ----

    async def search_characters(
        self, query: str, limit: int = 25, *, cache_ttl: Optional[int] = None
    ) -> List[dict]:
        """Search characters catalogue."""
        data = await self.get(
            "/characters",
            params={"q": query, "limit": limit, "order_by": "favorites", "sort": "desc"},
            cache_ttl=cache_ttl,
        )
        if not data or "data" not in data:
            return []
        return data["data"]

    async def get_character(
        self, mal_id: int, full: bool = True, *, cache_ttl: Optional[int] = None
    ) -> Optional[dict]:
        """Get character details by MAL ID."""
        path = f"/characters/{mal_id}/full" if full else f"/characters/{mal_id}"
        data = await self.get(path, cache_ttl=cache_ttl)
        if not data or "data" not in data:
            return None
        return data["data"]

    # ---- Staff / People Endpoints ----

    async def search_people(
        self, query: str, limit: int = 15, *, cache_ttl: Optional[int] = None
    ) -> List[dict]:
        """Search voice actors / staff members."""
        data = await self.get(
            "/people",
            params={"q": query, "limit": limit, "order_by": "favorites", "sort": "desc"},
            cache_ttl=cache_ttl,
        )
        if not data or "data" not in data:
            return []
        return data["data"]

    async def get_person(
        self, mal_id: int, full: bool = True, *, cache_ttl: Optional[int] = None
    ) -> Optional[dict]:
        """Get person details by MAL ID."""
        path = f"/people/{mal_id}/full" if full else f"/people/{mal_id}"
        data = await self.get(path, cache_ttl=cache_ttl)
        if not data or "data" not in data:
            return None
        return data["data"]

    # ---- Producer / Studio Endpoints ----

    async def search_producers(
        self, query: str, limit: int = 15, *, cache_ttl: Optional[int] = None
    ) -> List[dict]:
        """Search anime producers / studios."""
        data = await self.get(
            "/producers",
            params={"q": query, "limit": limit, "order_by": "favorites", "sort": "desc"},
            cache_ttl=cache_ttl,
        )
        if not data or "data" not in data:
            return []
        return data["data"]

    async def get_producer_anime(
        self, producer_id: int, limit: int = 25, *, cache_ttl: Optional[int] = None
    ) -> List[dict]:
        """Get anime produced by a producer/studio ID."""
        data = await self.get(
            "/anime",
            params={"producers": producer_id, "limit": limit, "order_by": "favorites", "sort": "desc"},
            cache_ttl=cache_ttl,
        )
        if not data or "data" not in data:
            return []
        return data["data"]
