"""7TV API client and emote models for AkaneBot without external library overhead."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
import typing as t

import aiohttp
import hikari as hk

from utils.errors import SevenTVError
from utils.models import ColorPalette as colors

logger = logging.getLogger(__name__)

SEVENTV_GQL_ENDPOINT = "https://7tv.io/v3/gql"

SEVENTV_SEARCH_QUERY = """
query SearchEmotes($query: String!, $page: Int, $limit: Int) {
    emotes(query: $query, page: $page, limit: $limit) {
        count
        items {
            id
            name
            animated
            owner {
                id
                username
                display_name
            }
            host {
                url
                files {
                    name
                    format
                    width
                    height
                    size
                }
            }
        }
    }
}
"""


@dataclass
class SevenTVEmote:
    """Represents an emote returned by the 7TV API."""
    id: str
    name: str
    animated: bool = False
    owner_name: t.Optional[str] = None
    host_url: str = ""
    files: list[dict[str, t.Any]] = field(default_factory=list)

    @property
    def base_url(self) -> str:
        """Normalized base URL for CDN assets."""
        url = self.host_url
        if url.startswith("//"):
            return f"https:{url}"
        elif url.startswith("http"):
            return url
        elif url:
            return f"https://{url}"
        return f"https://cdn.7tv.app/emote/{self.id}"

    @property
    def url_1x(self) -> str:
        return f"{self.base_url}/1x.webp"

    @property
    def url_2x(self) -> str:
        return f"{self.base_url}/2x.webp"

    @property
    def url_3x(self) -> str:
        return f"{self.base_url}/3x.webp"

    @property
    def url_4x(self) -> str:
        return f"{self.base_url}/4x.webp"

    @property
    def web_url(self) -> str:
        return f"https://7tv.app/emotes/{self.id}"

    def to_embed(self) -> hk.Embed:
        """Create a Discord embed representation of this 7TV emote."""
        embed = (
            hk.Embed(
                title=f"Emote: {self.name}",
                url=self.web_url,
                color=colors.DEFAULT,
            )
            .set_image(self.url_2x)
            .set_footer(text="Powered by 7tv")
            .add_field("Animated", "Yes" if self.animated else "No", inline=True)
            .add_field("Uploader", self.owner_name or "Unknown", inline=True)
            .add_field("ID", f"`{self.id}`", inline=True)
        )
        return embed


class SevenTVClient:
    """Asynchronous 7TV API client using standard aiohttp sessions."""

    def __init__(
        self,
        session: t.Optional[t.Union[aiohttp.ClientSession, t.Any]] = None,
        endpoint: str = SEVENTV_GQL_ENDPOINT,
    ) -> None:
        self._session = session
        self.endpoint = endpoint

    async def search_emotes(
        self,
        query: str,
        limit: int = 25,
        page: int = 1,
    ) -> list[SevenTVEmote]:
        """Search for emotes matching the query string on 7TV.

        Args:
            query: The search term or emote name.
            limit: Maximum number of emotes to retrieve (default 25).
            page: Page number for pagination (default 1).

        Returns:
            A list of SevenTVEmote objects.
        """
        if not query or not query.strip():
            return []

        close_session = False
        session = self._session
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            payload = {
                "query": SEVENTV_SEARCH_QUERY,
                "variables": {
                    "query": query.strip(),
                    "limit": limit,
                    "page": page,
                },
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "AkaneBot/1.0",
                "Accept-Encoding": "gzip, deflate",
            }

            async with session.post(self.endpoint, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise SevenTVError(f"7TV API HTTP {resp.status}: {text}")
                data = await resp.json()

            if "errors" in data and data["errors"]:
                raise SevenTVError(f"7TV GraphQL errors: {data['errors']}")

            emotes_data = data.get("data", {}).get("emotes", {})
            items = emotes_data.get("items", []) or []

            results: list[SevenTVEmote] = []
            for item in items:
                owner = item.get("owner") or {}
                owner_name = owner.get("display_name") or owner.get("username")
                host = item.get("host") or {}
                host_url = host.get("url") or f"//cdn.7tv.app/emote/{item['id']}"
                files = host.get("files") or []

                results.append(
                    SevenTVEmote(
                        id=item.get("id", ""),
                        name=item.get("name", "emote"),
                        animated=bool(item.get("animated", False)),
                        owner_name=owner_name,
                        host_url=host_url,
                        files=files,
                    )
                )
            return results
        except SevenTVError:
            raise
        except Exception as e:
            raise SevenTVError(f"Failed to query 7TV API: {e}") from e
        finally:
            if close_session and session:
                await session.close()
