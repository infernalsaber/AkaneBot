"""Domain classes wrapping AniList GraphQL responses.

Each class takes an AniListClient and returns typed objects from `from_*`
classmethods, or `None` / `[]` on a miss (never a raw error dict). Embed
construction lives alongside each class via `make_embed` / `make_pages`.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from operator import itemgetter
from typing import List, Optional, Set, Tuple

import hikari as hk

from utils.anilist_client import AniListClient, end_of_day_utc_ttl
from utils.errors import AniListError, MalError, MediaProviderError
from utils.misc import verbose_timedelta
from utils.models import ColorPalette as colors
from utils.mal_adapter import MalAdapter, MAL_ICON_URL, extract_primary_va
import logging

logger = logging.getLogger(__name__)


class AnilistBase:
    def __init__(self, name: str, id_: int) -> None:
        self.name = name
        self.id = id_

    @staticmethod
    def parse_description(description: str, limit: int = 400) -> str:
        """Parse an AniList description into Discord-friendly markdown."""
        if not description:
            return "-"

        problematic_tags = [
            "<i>", "</i>", "<I>", "</I>",
            "<b>", "</b>", "<B>", "</B>",
            "<br>", "<BR>", "#",
        ]
        for tag in problematic_tags:
            description = description.replace(tag, "")

        description = description.replace("~!", "||").replace("!~", "||")

        if len(description) > limit:
            description = description[:limit]
            if description.count("||") % 2:
                description += "||"
            description += "..."

        return description


class ALCharacter(AnilistBase):
    _FROM_SEARCH_QUERY = """
    query ($search: String) {
        Character (search: $search, sort: FAVOURITES_DESC) {
            id
            name { full }
        }
    }
    """

    _FROM_ID_QUERY = """
    query ($id: Int) {
        Character (id: $id, sort: FAVOURITES_DESC) {
            id
            name { full }
        }
    }
    """

    _IS_BIRTHDAY_SINGLE_QUERY = """
    query ($var: Boolean) {
        Character (isBirthday: $var, sort: FAVOURITES_DESC) {
            id
            name { full }
        }
    }
    """

    _SEARCH_MULTIPLE_QUERY = """
    query ($search: String, $perPage: Int) {
        Page (perPage: $perPage) {
            characters (search: $search, sort: FAVOURITES_DESC) {
                id
                name { full alternative }
                favourites
                description (asHtml: false)
                image { large }
                media { nodes { title { romaji english } } }
            }
        }
    }
    """

    _SERIES_CHARACTERS_QUERY = """
    query ($search: String) {
        Media (search: $search) {
            title { english romaji }
            characters (sort: FAVOURITES_DESC) {
                nodes {
                    id
                    name { full alternative }
                    favourites
                    description (asHtml: false)
                    image { large }
                    media { nodes { title { romaji english } } }
                }
            }
        }
    }
    """

    _BIRTHDAY_CHARACTERS_QUERY = """
    query {
        Page (perPage: 25) {
            characters (isBirthday: true, sort: FAVOURITES_DESC) {
                id
                name { full alternative }
                favourites
                description (asHtml: false)
                image { large }
                media { nodes { title { romaji english } } }
            }
        }
    }
    """

    _CHARACTER_MEDIA_QUERY = """
    query ($id: Int) {
        Character (id: $id) {
            id
            name { full }
            media { nodes { title { romaji english } type } }
        }
    }
    """

    _CHARACTER_DETAIL_QUERY = """
    query ($id: Int) {
        Character (id: $id, sort: FAVOURITES_DESC) {
            id
            name { full }
            image { large }
            gender
            dateOfBirth { year month day }
            description (asHtml: false)
            media (sort: POPULARITY_DESC, perPage: 25) {
                edges {
                    characterRole
                    node {
                        title { romaji }
                        season
                        seasonYear
                        meanScore
                        seasonInt
                        episodes
                        chapters
                        source
                        popularity
                        tags { name }
                    }
                    voiceActorRoles(language: JAPANESE) {
                        voiceActor {
                            id
                            name { full }
                            languageV2
                        }
                    }
                }
                nodes {
                    title { romaji }
                    season
                    seasonYear
                    meanScore
                    seasonInt
                    episodes
                    chapters
                    source
                    popularity
                    tags { name }
                }
            }
            favourites
            siteUrl
        }
    }
    """

    def __init__(self, name: str, id_: int, client: AniListClient) -> None:
        self.url = f"https://anilist.co/character/{id_}"
        self.client = client
        super().__init__(name, id_)

    @classmethod
    async def from_search(cls, query_: str, client: AniListClient) -> Optional["ALCharacter"]:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            try:
                results = await client.fallback.search_characters(query_, limit=1)
            except (MalError, Exception) as e:
                logger.warning(f"MAL fallback character search failed: {e}")
                results = []
            if not results:
                return None
            norm = MalAdapter.normalize_character(results[0])
            obj = cls(norm["name"]["full"], norm["id"], client)
            obj._data = norm
            return obj

        try:
            data = await client.query(cls._FROM_SEARCH_QUERY, {"search": query_})
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for character search '{query_}'; falling back to MAL")
                try:
                    results = await client.fallback.search_characters(query_, limit=1)
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback character search failed: {e}")
                    results = []
                if not results:
                    return None
                norm = MalAdapter.normalize_character(results[0])
                obj = cls(norm["name"]["full"], norm["id"], client)
                obj._data = norm
                return obj
            return None
        character = data.get("Character")
        if not character:
            return None
        return cls(character["name"]["full"], character["id"], client)

    @classmethod
    async def from_id(
        cls, id_: int, client: AniListClient, *, force_fallback: bool = False
    ) -> Optional["ALCharacter"]:
        if getattr(client, "fallback", None) and (force_fallback or not getattr(client, "is_available", True)):
            try:
                detail = await client.fallback.get_character(id_, full=True)
            except (MalError, Exception) as e:
                logger.warning(f"MAL fallback get_character failed: {e}")
                detail = None
            if not detail:
                return None
            norm = MalAdapter.normalize_character(detail)
            obj = cls(norm["name"]["full"], norm["id"], client)
            obj._data = norm
            obj._is_fallback = True
            return obj

        try:
            data = await client.query(cls._FROM_ID_QUERY, {"id": id_})
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for character id {id_}; falling back to MAL")
                try:
                    detail = await client.fallback.get_character(id_, full=True)
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback get_character failed: {e}")
                    detail = None
                if not detail:
                    return None
                norm = MalAdapter.normalize_character(detail)
                obj = cls(norm["name"]["full"], norm["id"], client)
                obj._data = norm
                obj._is_fallback = True
                return obj
            return None
        character = data.get("Character")
        if not character:
            return None
        return cls(character["name"]["full"], character["id"], client)

    @classmethod
    async def is_birthday(cls, client: AniListClient) -> Optional["ALCharacter"]:
        if not getattr(client, "is_available", True):
            return None
        try:
            data = await client.query(
                cls._IS_BIRTHDAY_SINGLE_QUERY,
                {"var": True},
                cache_ttl=end_of_day_utc_ttl(),
            )
        except AniListError:
            return None
        character = data.get("Character")
        if not character:
            return None
        return cls(character["name"]["full"], character["id"], client)

    @classmethod
    async def from_search_multiple(
        cls, query_: str, client: AniListClient, per_page: int = 10
    ) -> list:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            try:
                results = await client.fallback.search_characters(query_, limit=per_page)
            except (MalError, Exception) as e:
                logger.warning(f"MAL fallback character search failed: {e}")
                results = []
            return [MalAdapter.normalize_character(c) for c in results]

        try:
            data = await client.query(
                cls._SEARCH_MULTIPLE_QUERY,
                {"search": query_, "perPage": per_page},
            )
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for character search '{query_}'; falling back to MAL")
                try:
                    results = await client.fallback.search_characters(query_, limit=per_page)
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback character search failed: {e}")
                    results = []
                return [MalAdapter.normalize_character(c) for c in results]
            return []
        return data.get("Page", {}).get("characters", []) or []

    @classmethod
    async def from_series_characters(
        cls, series: str, client: AniListClient
    ) -> Tuple[Optional[str], list]:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            return await cls._mal_from_series_characters(series, client)

        try:
            data = await client.query(cls._SERIES_CHARACTERS_QUERY, {"search": series})
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for series characters '{series}'; falling back to MAL")
                return await cls._mal_from_series_characters(series, client)
            return None, []
        media = data.get("Media")
        if not media:
            return None, []
        title = media["title"]["english"] or media["title"]["romaji"]
        return title, media["characters"]["nodes"]

    @classmethod
    async def _mal_from_series_characters(
        cls, series: str, client: AniListClient
    ) -> Tuple[Optional[str], list]:
        if not getattr(client, "fallback", None):
            return None, []
        try:
            animes = await client.fallback.search_anime(series, limit=1)
            if not animes:
                return None, []
            anime = animes[0]
            title = anime.get("title_english") or anime.get("title")
            chars = await client.fallback.get_anime_characters(anime["mal_id"])
            norm_chars = []
            for c in chars:
                char_info = c.get("character", {})
                if char_info:
                    norm_chars.append(MalAdapter.normalize_character(char_info))
            return title, norm_chars
        except (MalError, Exception) as e:
            logger.warning(f"MAL fallback series characters failed: {e}")
            return None, []

    @classmethod
    async def get_birthday_characters(cls, client: AniListClient) -> list:
        if not getattr(client, "is_available", True):
            return []
        try:
            data = await client.query(
                cls._BIRTHDAY_CHARACTERS_QUERY,
                cache_ttl=end_of_day_utc_ttl(),
            )
        except AniListError:
            return []
        return data.get("Page", {}).get("characters", []) or []

    @classmethod
    async def get_character_media(cls, character_id: int, client: AniListClient) -> Optional[dict]:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            return await cls._mal_get_character_media(character_id, client)

        try:
            data = await client.query(cls._CHARACTER_MEDIA_QUERY, {"id": character_id})
        except AniListError:
            if getattr(client, "fallback", None):
                return await cls._mal_get_character_media(character_id, client)
            return None
        character = data.get("Character")
        if not character:
            return None

        media_titles = [
            m["title"]["english"] or m["title"]["romaji"]
            for m in character["media"]["nodes"]
            if m["title"]["english"] or m["title"]["romaji"]
        ]
        return {
            "id": character["id"],
            "name": character["name"]["full"],
            "media_titles": media_titles,
        }

    @classmethod
    async def _mal_get_character_media(
        cls, character_id: int, client: AniListClient
    ) -> Optional[dict]:
        if not getattr(client, "fallback", None):
            return None
        try:
            detail = await client.fallback.get_character(character_id, full=True)
            if not detail:
                return None
            norm = MalAdapter.normalize_character(detail)
            media_titles = [
                n["title"]["romaji"]
                for n in norm["media"]["nodes"]
                if n.get("title")
            ]
            return {
                "id": norm["id"],
                "name": norm["name"]["full"],
                "media_titles": media_titles,
            }
        except (MalError, Exception) as e:
            logger.warning(f"MAL fallback get_character_media failed: {e}")
            return None

    async def _fetch_detail(self) -> Optional[dict]:
        if hasattr(self, "_data") and self._data:
            return self._data
        force_fallback = getattr(self, "_is_fallback", False)
        if getattr(self.client, "fallback", None) and (force_fallback or not getattr(self.client, "is_available", True)):
            try:
                detail = await self.client.fallback.get_character(self.id, full=True)
                if detail:
                    self._data = MalAdapter.normalize_character(detail)
                    self._is_fallback = True
                    return self._data
            except (MalError, Exception) as e:
                logger.warning(f"MAL fallback _fetch_detail failed: {e}")
            return None

        try:
            data = await self.client.query(self._CHARACTER_DETAIL_QUERY, {"id": self.id})
        except AniListError:
            if getattr(self.client, "fallback", None):
                logger.info(f"AniList failed for character detail {self.id}; falling back to MAL")
                try:
                    detail = await self.client.fallback.get_character(self.id, full=True)
                    if detail:
                        self._data = MalAdapter.normalize_character(detail)
                        return self._data
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback _fetch_detail failed: {e}")
            return None
        return data.get("Character")

    def _format_dob(self, dob: dict) -> str:
        if dob and dob.get("month") and dob.get("day"):
            out = f"{dob['day']}/{dob['month']}"
            if dob.get("year"):
                out += f"/{dob['year']}"
            return out
        return "NA"

    @staticmethod
    def get_primary_va(response: dict) -> str:
        """Determine primary Japanese voice actor by counting occurrences across media edges."""
        edges = (response.get("media") or {}).get("edges", [])
        va_counts: dict[tuple[int, str], int] = {}

        for edge in edges:
            for role in edge.get("voiceActorRoles", []) or []:
                va = role.get("voiceActor")
                if va and va.get("id") and va.get("name", {}).get("full"):
                    lang = va.get("languageV2")
                    if lang and lang.lower() != "japanese":
                        continue
                    key = (va["id"], va["name"]["full"])
                    va_counts[key] = va_counts.get(key, 0) + 1

        if not va_counts:
            return "NA"

        best_va, _ = max(va_counts.items(), key=lambda item: item[1])
        va_id, va_name = best_va
        return f"[{va_name}](https://anilist.co/staff/{va_id})"

    async def make_embed(self) -> hk.Embed:
        response = await self._fetch_detail()
        if not response:
            return hk.Embed(
                title="ERROR FETCHING DATA",
                color=colors.ERROR,
                description=(
                    "Failed to fetch data 😵"
                    "\nTry typing the full name of the character."
                ),
            )

        is_fallback = response.get("_is_fallback", False)
        footer_text = response.get("_source", "Source: AniList") if is_fallback else "Source: AniList"
        footer_icon = (
            response.get("_source_icon", MAL_ICON_URL)
            if is_fallback
            else "https://anilist.co/img/icons/android-chrome-512x512.png"
        )

        dob = self._format_dob(response.get("dateOfBirth"))
        description = (
            self.parse_description(response["description"])
            if response.get("description") else "NA"
        )
        if is_fallback and "voices" in response:
            primary_va = extract_primary_va(response["voices"])
        else:
            primary_va = self.get_primary_va(response)

        return (
            hk.Embed(
                title=self.name,
                url=response.get("siteUrl") or self.url,
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Gender", response.get("gender") or "Unknown")
            .add_field("DOB", dob, inline=True)
            .add_field("Favourites", f"{response.get('favourites', 0)}❤", inline=True)
            .add_field("Character Description", description)
            .add_field("Primary Voice Actor", primary_va, inline=False)
            .set_thumbnail(response.get("image", {}).get("large"))
            .set_footer(
                text=footer_text,
                icon=footer_icon,
            )
        )

    async def make_pages(self) -> List[hk.Embed]:
        response = await self._fetch_detail()
        if not response:
            return [
                hk.Embed(
                    title="ERROR FETCHING DATA",
                    color=colors.ERROR,
                    description=(
                        "Failed to fetch data 😵"
                        "\nTry typing the full name of the character."
                    ),
                )
            ]

        title = response["name"]["full"]
        dob = self._format_dob(response.get("dateOfBirth"))
        description = (
            self.parse_description(response["description"])
            if response.get("description") else "NA"
        )
        is_fallback = response.get("_is_fallback", False)
        if is_fallback and "voices" in response:
            primary_va = extract_primary_va(response["voices"])
        else:
            primary_va = self.get_primary_va(response)

        series = ""
        nodes = (response.get("media") or {}).get("nodes", [])
        for i, item in enumerate(nodes[:3]):
            score = item.get('meanScore', 'NA')
            series += (
                f"```ansi\n{i+1}. \u001b[0;35m{item['title']['romaji']}"
                f" \u001b[0;32m({score})```"
            )

        footer = {
            "text": response.get("_source", "Source: AniList") if is_fallback else "Source: AniList",
            "icon": response.get("_source_icon", MAL_ICON_URL) if is_fallback else "https://anilist.co/img/icons/android-chrome-512x512.png",
        }

        return [
            hk.Embed(
                title=title,
                url=response.get("siteUrl") or self.url,
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Gender", response.get("gender") or "Unknown")
            .add_field("DOB", dob, inline=True)
            .add_field("Favourites", f"{response.get('favourites', 0)}❤", inline=True)
            .add_field("Character Description", description)
            .add_field("Primary Voice Actor", primary_va, inline=False)
            .set_thumbnail(response.get("image", {}).get("large"))
            .set_footer(**footer),
            hk.Embed(
                title=title,
                url=response.get("siteUrl") or self.url,
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .set_thumbnail(response.get("image", {}).get("large"))
            .set_footer(**footer)
            .add_field("Appears in ", series),
        ]


class ALAnime(AnilistBase):
    _FROM_ID_QUERY = """
    query ($id: Int, $type: MediaType) {
        Media (id: $id, type: $type) {
            id
            idMal
            title { english romaji }
            duration
            type
            averageScore
            format
            meanScore
            episodes
            startDate { year }
            coverImage { large }
            studios (isMain: true) { nodes { name siteUrl } }
            bannerImage
            genres
            status
            description (asHtml: false)
            siteUrl
            trailer { id site thumbnail }
        }
    }
    """

    _SEARCH_QUERY = """
    query ($search: String, $type: MediaType) {
        Page (perPage: 10) {
            media (search: $search, type: $type) {
                id
                idMal
                title { english romaji }
                duration
                type
                averageScore
                format
                meanScore
                episodes
                startDate { year }
                coverImage { large }
                studios (isMain: true) { nodes { name siteUrl } }
                bannerImage
                genres
                status
                description (asHtml: false)
                siteUrl
                nextAiringEpisode { episode }
                trailer { id site thumbnail }
            }
        }
    }
    """

    _LINK_LOOKUP_QUERY = """
    query ($id: Int, $type: MediaType) {
        Media (id: $id, type: $type, sort: POPULARITY_DESC) {
            id
            idMal
            title { english romaji }
            type
            averageScore
            format
            meanScore
            chapters
            episodes
            startDate { year }
            coverImage { large }
            bannerImage
            genres
            status
            description (asHtml: false)
            siteUrl
        }
    }
    """

    def __init__(self, name: str, id_: int, client: AniListClient) -> None:
        self.url = f"https://anilist.co/anime/{id_}"
        self.client = client
        super().__init__(name, id_)

    @classmethod
    async def from_search_multiple(
        cls, query_: str, client: AniListClient
    ) -> list:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            try:
                mal_data = await client.fallback.search_anime(query_)
            except (MalError, Exception) as e:
                logger.warning(f"MAL fallback search_anime failed: {e}")
                mal_data = []
            return [MalAdapter.normalize_anime(a) for a in mal_data]

        try:
            data = await client.query(
                cls._SEARCH_QUERY,
                {"search": query_, "type": "ANIME"},
            )
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for anime search '{query_}'; falling back to MAL")
                try:
                    mal_data = await client.fallback.search_anime(query_)
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback search_anime failed: {e}")
                    mal_data = []
                return [MalAdapter.normalize_anime(a) for a in mal_data]
            return []
        return data.get("Page", {}).get("media", []) or []

    @classmethod
    async def from_id(
        cls, id_: int, client: AniListClient, *, force_fallback: bool = False
    ) -> Optional["ALAnime"]:
        if getattr(client, "fallback", None) and (force_fallback or not getattr(client, "is_available", True)):
            try:
                detail = await client.fallback.get_anime(id_, full=True)
            except (MalError, Exception) as e:
                logger.warning(f"MAL fallback get_anime failed: {e}")
                detail = None
            if not detail:
                return None
            norm = MalAdapter.normalize_anime(detail)
            title = norm["title"]["english"] or norm["title"]["romaji"]
            obj = cls(title, norm["id"], client)
            obj._data = norm
            obj._is_fallback = True
            return obj

        try:
            data = await client.query(cls._FROM_ID_QUERY, {"id": id_, "type": "ANIME"})
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for anime id {id_}; falling back to MAL")
                try:
                    detail = await client.fallback.get_anime(id_, full=True)
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback get_anime failed: {e}")
                    detail = None
                if not detail:
                    return None
                norm = MalAdapter.normalize_anime(detail)
                title = norm["title"]["english"] or norm["title"]["romaji"]
                obj = cls(title, norm["id"], client)
                obj._data = norm
                obj._is_fallback = True
                return obj
            return None
        media = data.get("Media")
        if not media:
            return None
        title = media["title"]["english"] or media["title"]["romaji"]
        obj = cls(title, media["id"], client)
        obj._data = media
        return obj

    @classmethod
    async def lookup_by_link(
        cls, id_: int, type_: str, client: AniListClient
    ) -> Optional[dict]:
        """Returns raw media dict from the link-sharing listener path."""
        try:
            data = await client.query(
                cls._LINK_LOOKUP_QUERY,
                {"id": id_, "type": type_},
            )
        except AniListError:
            return None
        return data.get("Media")

    async def make_embed(self):
        media = getattr(self, "_data", None)
        if media is None:
            if getattr(self.client, "fallback", None) and not getattr(self.client, "is_available", True):
                try:
                    detail = await self.client.fallback.get_anime(self.id, full=True)
                    if detail:
                        media = MalAdapter.normalize_anime(detail)
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback make_embed failed: {e}")
            if media is None:
                try:
                    data = await self.client.query(
                        self._FROM_ID_QUERY, {"id": self.id, "type": "ANIME"}
                    )
                    media = data.get("Media")
                except AniListError:
                    if getattr(self.client, "fallback", None):
                        try:
                            detail = await self.client.fallback.get_anime(self.id, full=True)
                            if detail:
                                media = MalAdapter.normalize_anime(detail)
                        except (MalError, Exception) as e:
                            logger.warning(f"MAL fallback make_embed failed: {e}")
            if not media:
                return None

        title = media["title"]["english"] or media["title"]["romaji"]
        no_of_items = (
            media["episodes"]
            if media["episodes"] != 1
            else verbose_timedelta(timedelta(minutes=media.get("duration") or 24))
        )
        description = (
            self.parse_description(media["description"])
            if media.get("description") else "NA"
        )
        studios = media.get("studios", {}).get("nodes", [])

        is_fallback = media.get("_is_fallback", False)
        footer_text = media.get("_source", "Source: AniList") if is_fallback else "Source: AniList"
        footer_icon = (
            media.get("_source_icon", MAL_ICON_URL)
            if is_fallback
            else "https://anilist.co/img/icons/android-chrome-512x512.png"
        )

        embed = (
            hk.Embed(
                title=title,
                url=media["siteUrl"],
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Rating", media.get("meanScore", "NA"))
            .add_field("Genres", ", ".join(media.get("genres", [])[:4]))
            .add_field("Status", (media.get("status") or "NA").replace("_", " "), inline=True)
            .add_field(
                "Episodes" if media["episodes"] != 1 else "Duration",
                no_of_items,
                inline=True,
            )
            .add_field("Studio", studios[0]["name"] if studios else "Unknown", inline=True)
            .add_field("Summary", description)
            .set_thumbnail(media.get("coverImage", {}).get("large"))
            .set_image(media.get("bannerImage"))
            .set_footer(
                text=footer_text,
                icon=footer_icon,
            )
        )

        trailer = None
        if media.get("trailer"):
            site = media["trailer"].get("site")
            vid = media["trailer"].get("id")
            if site == "youtube":
                trailer = f"https://youtube.com/watch?v={vid}"
            elif site:
                trailer = f"https://{site}.com/video/{vid}"

        return [embed, trailer]

    # ---- Watch-order (recursive relation walk) ----

    _RELATIONS_QUERY = """
    query ($id: Int, $search: String) {
        Media(id: $id, search: $search, type: ANIME) {
            id
            title { english romaji }
            startDate { year month day }
            duration
            episodes
            relations {
                edges {
                    relationType
                    node { id title { english romaji } type }
                }
            }
        }
    }
    """

    @classmethod
    async def get_anime_data(
        cls,
        client: AniListClient,
        *,
        anime_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> dict:
        """Return the raw Media dict (id/title/duration/episodes/relations)."""
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            return await cls._get_mal_anime_data(client, anime_id=anime_id, search=search)

        variables = {"id": anime_id} if anime_id else {"search": search}
        try:
            return await client.query(cls._RELATIONS_QUERY, variables)
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for anime relations; falling back to MAL")
                return await cls._get_mal_anime_data(client, anime_id=anime_id, search=search)
            return {}

    @classmethod
    async def _get_mal_anime_data(
        cls,
        client: AniListClient,
        *,
        anime_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> dict:
        if not getattr(client, "fallback", None):
            return {}
        try:
            if not anime_id and search:
                results = await client.fallback.search_anime(search, limit=1)
                if not results:
                    return {}
                anime_id = results[0]["mal_id"]
            if not anime_id:
                return {}

            anime_full = await client.fallback.get_anime(anime_id, full=True)
            if not anime_full:
                return {}

            relations_raw = await client.fallback.get_anime_relations(anime_id)
        except (MalError, Exception) as e:
            logger.warning(f"MAL fallback _get_mal_anime_data failed for anime_id={anime_id}: {e}")
            return {}

        edges = []
        for rel in relations_raw:
            rel_type = rel.get("relation", "").upper().replace(" ", "_")
            for entry in rel.get("entry", []):
                if entry.get("type") == "anime":
                    edges.append({
                        "relationType": rel_type,
                        "node": {
                            "id": entry.get("mal_id"),
                            "title": {
                                "english": entry.get("name"),
                                "romaji": entry.get("name"),
                            },
                            "type": "ANIME",
                        }
                    })

        aired_from = anime_full.get("aired", {}).get("prop", {}).get("from", {})
        return {
            "Media": {
                "id": anime_id,
                "title": {
                    "english": anime_full.get("title_english") or anime_full.get("title"),
                    "romaji": anime_full.get("title"),
                },
                "startDate": {
                    "year": aired_from.get("year"),
                    "month": aired_from.get("month"),
                    "day": aired_from.get("day"),
                },
                "duration": MalAdapter.normalize_anime(anime_full).get("duration"),
                "episodes": anime_full.get("episodes"),
                "relations": {"edges": edges},
                "siteUrl": anime_full.get("url") or f"https://myanimelist.net/anime/{anime_id}",
            }
        }

    @classmethod
    async def get_complete_series(
        cls,
        client: AniListClient,
        anime_id: int,
        visited: Optional[Set[int]] = None,
    ) -> list:
        """Recursively gather all anime related by PREQUEL/SEQUEL/SIDE_STORY."""
        from utils.anilist_graph import AnimeNode

        if visited is None:
            visited = set()
        if anime_id in visited:
            return []
        visited.add(anime_id)

        try:
            data = await cls.get_anime_data(client, anime_id=anime_id)
        except (AniListError, MalError):
            return []

        media = data.get("Media")
        if not media:
            return []

        title = media["title"]["english"] or media["title"]["romaji"]
        url = media.get("siteUrl")
        if not url:
            if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
                url = f"https://myanimelist.net/anime/{media['id']}"
            else:
                url = f"https://anilist.co/anime/{media['id']}"

        entries = [
            AnimeNode(
                media["id"],
                title,
                media["startDate"],
                media.get("duration", 0),
                media.get("episodes", 1),
                url=url,
            )
        ]

        for edge in (media.get("relations") or {}).get("edges", []):
            node = edge["node"]
            if node["type"] == "ANIME" and edge["relationType"] in (
                "PREQUEL",
                "SEQUEL",
                "SIDE_STORY",
                "PARENT",
                "ALTERNATIVE",
                "SPIN_OFF",
                "SUMMARY",
            ):
                try:
                    entries.extend(
                        await cls.get_complete_series(client, node["id"], visited)
                    )
                except (AniListError, MalError):
                    continue

        return entries

    @classmethod
    async def format_chronological_order(
        cls, client: AniListClient, anime_id: int
    ) -> list:
        """Watch order by release date; undated entries appended at the end."""
        entries = await cls.get_complete_series(client, anime_id)
        if not entries:
            return []
        dated = [e for e in entries if e.date is not None]
        undated = [e for e in entries if e.date is None]
        dated.sort(key=lambda x: x.date)
        return dated + undated

    # ---- Airtime trend plot ----

    _TRENDS_MEDIA_QUERY = """
    query ($search: String) {
        Media (search: $search, type: ANIME) {
            id
            title { english romaji }
            averageScore
            startDate { year month day }
            endDate { year month day }
            coverImage { large }
            status
        }
    }
    """

    _TRENDS_PAGE_QUERY = """
    query ($id: Int, $page: Int, $perpage: Int, $date_greater: Int, $date_lesser: Int) {
        Page (page: $page, perPage: $perpage) {
            pageInfo { total hasNextPage }
            mediaTrends (mediaId: $id, date_greater: $date_greater, date_lesser: $date_lesser) {
                mediaId
                date
                trending
                averageScore
                episode
            }
        }
    }
    """

    @classmethod
    async def fetch_trends(cls, client: AniListClient, search_query: str) -> dict:
        """Return the activity / episodes / scores trend data for an anime."""
        if not getattr(client, "is_available", True):
            raise AniListError(
                "AniList API is currently unavailable. Anime trend analytics require AniList."
            )

        try:
            data = await client.query(cls._TRENDS_MEDIA_QUERY, {"search": search_query})
        except AniListError as e:
            raise AniListError(f"AniList API error retrieving trends: {e}") from e

        media = data.get("Media")
        if not media:
            raise AniListError(f"No anime found for '{search_query}'")

        al_id = media["id"]
        name = media["title"]["english"] or media["title"]["romaji"]

        start = media["startDate"]
        lower_limit = datetime(
            start["year"], start["month"], start["day"], 0, 0
        ) - timedelta(days=7)

        end = media["endDate"]
        if end["year"]:
            upper_limit = datetime(end["year"], end["month"], end["day"], 0, 0) + timedelta(days=7)
        else:
            upper_limit = datetime.now()

        trend_score: list[dict] = []
        page = 1
        while True:
            try:
                page_data = await client.query(
                    cls._TRENDS_PAGE_QUERY,
                    {
                        "id": al_id,
                        "page": page,
                        "perpage": 50,
                        "date_greater": int(lower_limit.timestamp()),
                        "date_lesser": int(upper_limit.timestamp()),
                    },
                )
            except AniListError as e:
                raise AniListError(f"AniList API error retrieving trends: {e}") from e

            page_info = page_data["Page"]["pageInfo"]
            trend_score.extend(page_data["Page"]["mediaTrends"])
            if not page_info["hasNextPage"]:
                break
            page += 1

        dates: list[datetime] = []
        trends: list[int] = []
        scores: list[int] = []
        episode_dates: list[datetime] = []
        episode_trends: list[int] = []

        for v in sorted((e for e in trend_score if e["episode"]), key=itemgetter("date")):
            episode_dates.append(datetime.fromtimestamp(v["date"]))
            episode_trends.append(v["trending"])

        for v in sorted(trend_score, key=itemgetter("date")):
            dates.append(datetime.fromtimestamp(v["date"]))
            trends.append(v["trending"])
            if v["averageScore"]:
                scores.append(v["averageScore"])

        return {
            "name": name,
            "data": {
                "activity": {"dates": dates, "values": trends},
                "episodes": {"dates": episode_dates, "values": episode_trends},
                "scores": {"dates": dates[-len(scores):], "values": scores},
            },
        }


class ALManga(AnilistBase):
    _SEARCH_QUERY = """
    query ($search: String, $type: MediaType) {
        Page (perPage: 5) {
            media (search: $search, type: $type,
                   sort: POPULARITY_DESC, format_in: [MANGA, ONE_SHOT]) {
                id
                idMal
                title { english romaji }
                type
                averageScore
                format
                meanScore
                chapters
                episodes
                startDate { year }
                coverImage { large }
                bannerImage
                genres
                status
                description (asHtml: false)
                siteUrl
            }
        }
    }
    """

    def __init__(self, name: str, id_: int, client: AniListClient) -> None:
        self.url = f"https://anilist.co/manga/{id_}"
        self.client = client
        super().__init__(name, id_)

    @classmethod
    async def from_search_multiple(cls, query_: str, client: AniListClient) -> list:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            try:
                mal_data = await client.fallback.search_manga(query_)
            except (MalError, Exception) as e:
                logger.warning(f"MAL fallback search_manga failed: {e}")
                mal_data = []
            return [MalAdapter.normalize_manga(m) for m in mal_data]

        try:
            data = await client.query(
                cls._SEARCH_QUERY,
                {"search": query_, "type": "MANGA"},
            )
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for manga search '{query_}'; falling back to MAL")
                try:
                    mal_data = await client.fallback.search_manga(query_)
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback search_manga failed: {e}")
                    mal_data = []
                return [MalAdapter.normalize_manga(m) for m in mal_data]
            return []
        return data.get("Page", {}).get("media", []) or []

    _URL_FROM_MAL_QUERY = """
    query ($mal_id: Int, $search: String) {
        Media (idMal: $mal_id, search: $search, type: MANGA) {
            siteUrl
        }
    }
    """

    @classmethod
    async def al_url_from_mal(
        cls,
        client: AniListClient,
        *,
        mal_id: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve the AniList URL for a manga given its MAL id or a title."""
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            if mal_id:
                return f"https://myanimelist.net/manga/{mal_id}"
            if name:
                try:
                    results = await client.fallback.search_manga(name, limit=1)
                    if results:
                        return results[0].get("url")
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback search_manga for url failed: {e}")
            return None

        try:
            data = await client.query(
                cls._URL_FROM_MAL_QUERY,
                {"mal_id": mal_id, "search": name},
            )
        except AniListError:
            if getattr(client, "fallback", None):
                if mal_id:
                    return f"https://myanimelist.net/manga/{mal_id}"
                if name:
                    try:
                        results = await client.fallback.search_manga(name, limit=1)
                        if results:
                            return results[0].get("url")
                    except (MalError, Exception) as e:
                        logger.warning(f"MAL fallback search_manga for url failed: {e}")
            return None
        media = data.get("Media")
        return media["siteUrl"] if media else None


class ALNovel(AnilistBase):
    _SEARCH_QUERY = """
    query ($search: String, $type: MediaType) {
        Page (perPage: 10) {
            media (search: $search, type: $type,
                   sort: POPULARITY_DESC, format_in: [NOVEL]) {
                id
                idMal
                title { english romaji }
                type
                averageScore
                format
                meanScore
                volumes
                startDate { year }
                coverImage { large }
                bannerImage
                genres
                status
                description (asHtml: false)
                siteUrl
            }
        }
    }
    """

    _FROM_SEARCH_QUERY = """
    query ($search: String, $type: MediaType) {
        Media (search: $search, type: $type,
               sort: POPULARITY_DESC, format_in: [NOVEL]) {
            id
            idMal
            title { english romaji }
            type
            averageScore
            format
            meanScore
            volumes
            startDate { year }
            coverImage { large }
            bannerImage
            genres
            status
            description (asHtml: false)
            siteUrl
        }
    }
    """

    def __init__(self, name: str, id_: int, client: AniListClient) -> None:
        self.url = f"https://anilist.co/manga/{id_}"
        self.client = client
        super().__init__(name, id_)

    @classmethod
    async def from_search_multiple(cls, query_: str, client: AniListClient) -> list:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            try:
                mal_data = await client.fallback.search_manga(query_, type_="lightnovel")
            except (MalError, Exception) as e:
                logger.warning(f"MAL fallback search_manga (novel) failed: {e}")
                mal_data = []
            return [MalAdapter.normalize_manga(m, is_novel=True) for m in mal_data]

        try:
            data = await client.query(
                cls._SEARCH_QUERY,
                {"search": query_, "type": "MANGA"},
            )
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for novel search '{query_}'; falling back to MAL")
                try:
                    mal_data = await client.fallback.search_manga(query_, type_="lightnovel")
                except (MalError, Exception) as e:
                    logger.warning(f"MAL fallback search_manga (novel) failed: {e}")
                    mal_data = []
                return [MalAdapter.normalize_manga(m, is_novel=True) for m in mal_data]
            return []
        return data.get("Page", {}).get("media", []) or []

    @classmethod
    async def from_search(cls, query_: str, client: AniListClient) -> Optional[dict]:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            results = await cls.from_search_multiple(query_, client)
            return results[0] if results else None

        try:
            data = await client.query(
                cls._FROM_SEARCH_QUERY,
                {"search": query_, "type": "MANGA"},
            )
        except AniListError:
            if getattr(client, "fallback", None):
                results = await cls.from_search_multiple(query_, client)
                return results[0] if results else None
            return None
        return data.get("Media")


class ALUser(AnilistBase):
    _QUERY = """
    query ($name: String) {
        User(name: $name) {
            id
            name
            about
            avatar { medium }
        }
    }
    """

    def __init__(self, name: str, id_: int, client: AniListClient) -> None:
        self.url = f"https://anilist.co/user/{name}"
        self.client = client
        super().__init__(name, id_)

    @classmethod
    async def from_name(cls, name: str, client: AniListClient) -> Optional["ALUser"]:
        try:
            data = await client.query(cls._QUERY, {"name": name})
        except AniListError:
            return None
        user = data.get("User")
        if not user:
            return None
        obj = cls(user["name"], user["id"], client)
        obj._data = user
        return obj


class ALStudio(AnilistBase):
    _QUERY = """
    fragment MediaFields on Media {
        id
        title { english romaji }
        coverImage { large }
        averageScore
        popularity
        favourites
        relations {
            edges {
                relationType
                node {
                    id
                    type
                    relations {
                        edges {
                            relationType
                            node {
                                id
                                type
                                relations {
                                    edges {
                                        relationType
                                        node {
                                            id
                                            type
                                            relations {
                                                edges {
                                                    relationType
                                                    node {
                                                        id
                                                        type
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    query ($search: String, $sort: [MediaSort]) {
        Studio(search: $search) {
            name
            siteUrl
            id
            favourites
            media(sort: $sort, page: 1, perPage: 25) {
                nodes {
                    ...MediaFields
                }
            }
            media2: media(sort: $sort, page: 2, perPage: 25) {
                nodes {
                    ...MediaFields
                }
            }
        }
    }
    """

    def __init__(self, name: str, id_: int, client: AniListClient) -> None:
        self.url = f"https://anilist.co/studio/{id_}"
        self.client = client
        super().__init__(name, id_)

    @classmethod
    async def from_search(
        cls, query_: str, client: AniListClient, per_page: int = 50, cache_ttl: Optional[int] = None
    ) -> Optional[dict]:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            return await cls._mal_from_search(query_, client, per_page=per_page)

        try:
            data = await client.query(
                cls._QUERY,
                {"search": query_, "sort": "FAVOURITES_DESC"},
                cache_ttl=cache_ttl,
            )
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for studio search '{query_}'; falling back to MAL")
                return await cls._mal_from_search(query_, client, per_page=per_page)
            return None
        studio = data.get("Studio")
        if studio:
            nodes1 = studio.get("media", {}).get("nodes", [])
            nodes2 = studio.get("media2", {}).get("nodes", [])
            media_nodes = nodes1 + nodes2
            studio["media_nodes"] = media_nodes
            if media_nodes:
                first_node = media_nodes[0]
                if first_node.get("id") is None and cache_ttl != 0:
                    return await cls.from_search(query_, client, per_page=per_page, cache_ttl=0)
        return studio

    @classmethod
    async def _mal_from_search(
        cls, query_: str, client: AniListClient, per_page: int = 50
    ) -> Optional[dict]:
        if not getattr(client, "fallback", None):
            return None
        try:
            producers = await client.fallback.search_producers(query_, limit=1)
            if not producers:
                return None
            producer = producers[0]
            anime_list = await client.fallback.get_producer_anime(producer["mal_id"], limit=per_page)
            return MalAdapter.normalize_studio(producer, anime_list)
        except (MalError, Exception) as e:
            logger.warning(f"MAL fallback studio search failed: {e}")
            return None


class ALStaff(AnilistBase):
    _QUERY = """
    query ($search: String, $sort: [MediaSort], $charactersSort: [CharacterSort], $perPage: Int) {
        Staff(search: $search) {
            dateOfBirth { year month day }
            age
            gender
            favourites
            description
            image { medium }
            name { full }
            yearsActive
            siteUrl
            characters(sort: $charactersSort, perPage: $perPage) {
                nodes {
                    favourites
                    name { full }
                    image { medium }
                    media(sort: $sort) {
                        nodes {
                            title { english romaji }
                            type
                            favourites
                        }
                    }
                }
            }
        }
    }
    """

    def __init__(self, name: str, id_: int, client: AniListClient) -> None:
        self.url = f"https://anilist.co/staff/{id_}"
        self.client = client
        super().__init__(name, id_)

    @classmethod
    async def from_search(
        cls, query_: str, client: AniListClient, per_page: int = 12
    ) -> Optional[dict]:
        if getattr(client, "fallback", None) and not getattr(client, "is_available", True):
            return await cls._mal_from_search(query_, client, per_page=per_page)

        try:
            data = await client.query(
                cls._QUERY,
                {
                    "search": query_,
                    "sort": "FAVOURITES_DESC",
                    "charactersSort": "FAVOURITES_DESC",
                    "perPage": per_page,
                },
            )
        except AniListError:
            if getattr(client, "fallback", None):
                logger.info(f"AniList failed for staff search '{query_}'; falling back to MAL")
                return await cls._mal_from_search(query_, client, per_page=per_page)
            return None
        return data.get("Staff")

    @classmethod
    async def _mal_from_search(
        cls, query_: str, client: AniListClient, per_page: int = 12
    ) -> Optional[dict]:
        if not getattr(client, "fallback", None):
            return None
        try:
            people = await client.fallback.search_people(query_, limit=1)
            if not people:
                return None
            person = await client.fallback.get_person(people[0]["mal_id"], full=True)
            if not person:
                return None
            return MalAdapter.normalize_staff(person)
        except (MalError, Exception) as e:
            logger.warning(f"MAL fallback staff search failed: {e}")
            return None

