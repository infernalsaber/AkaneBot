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
from utils.errors import AniListError
from utils.misc import verbose_timedelta
from utils.models import ColorPalette as colors


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
            media (sort: TRENDING_DESC, perPage: 3) {
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
        try:
            data = await client.query(cls._FROM_SEARCH_QUERY, {"search": query_})
        except AniListError:
            return None
        character = data.get("Character")
        if not character:
            return None
        return cls(character["name"]["full"], character["id"], client)

    @classmethod
    async def from_id(cls, id_: int, client: AniListClient) -> Optional["ALCharacter"]:
        try:
            data = await client.query(cls._FROM_ID_QUERY, {"id": id_})
        except AniListError:
            return None
        character = data.get("Character")
        if not character:
            return None
        return cls(character["name"]["full"], character["id"], client)

    @classmethod
    async def is_birthday(cls, client: AniListClient) -> Optional["ALCharacter"]:
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
        try:
            data = await client.query(
                cls._SEARCH_MULTIPLE_QUERY,
                {"search": query_, "perPage": per_page},
            )
        except AniListError:
            return []
        return data.get("Page", {}).get("characters", []) or []

    @classmethod
    async def from_series_characters(
        cls, series: str, client: AniListClient
    ) -> Tuple[Optional[str], list]:
        try:
            data = await client.query(cls._SERIES_CHARACTERS_QUERY, {"search": series})
        except AniListError:
            return None, []
        media = data.get("Media")
        if not media:
            return None, []
        title = media["title"]["english"] or media["title"]["romaji"]
        return title, media["characters"]["nodes"]

    @classmethod
    async def get_birthday_characters(cls, client: AniListClient) -> list:
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
        try:
            data = await client.query(cls._CHARACTER_MEDIA_QUERY, {"id": character_id})
        except AniListError:
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

    async def _fetch_detail(self) -> Optional[dict]:
        try:
            data = await self.client.query(self._CHARACTER_DETAIL_QUERY, {"id": self.id})
        except AniListError:
            return None
        return data.get("Character")

    def _format_dob(self, dob: dict) -> str:
        if dob and dob.get("month") and dob.get("day"):
            out = f"{dob['day']}/{dob['month']}"
            if dob.get("year"):
                out += f"/{dob['year']}"
            return out
        return "NA"

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

        dob = self._format_dob(response["dateOfBirth"])
        description = (
            self.parse_description(response["description"])
            if response["description"] else "NA"
        )

        return (
            hk.Embed(
                title=self.name,
                url=self.url,
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Gender", response["gender"] or "Unknown")
            .add_field("DOB", dob, inline=True)
            .add_field("Favourites", f"{response['favourites']}❤", inline=True)
            .add_field("Character Description", description)
            .set_thumbnail(response["image"]["large"])
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
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
        dob = self._format_dob(response["dateOfBirth"])
        description = (
            self.parse_description(response["description"])
            if response["description"] else "NA"
        )

        series = ""
        for i, item in enumerate(response["media"]["nodes"]):
            series += (
                f"```ansi\n{i+1}. \u001b[0;35m{item['title']['romaji']}"
                f" \u001b[0;32m({item['meanScore']})```"
            )

        footer = {
            "text": "Source: AniList",
            "icon": "https://anilist.co/img/icons/android-chrome-512x512.png",
        }

        return [
            hk.Embed(
                title=title,
                url=response["siteUrl"],
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Gender", response["gender"] or "Unknown")
            .add_field("DOB", dob, inline=True)
            .add_field("Favourites", f"{response['favourites']}❤", inline=True)
            .add_field("Character Description", description)
            .set_thumbnail(response["image"]["large"])
            .set_footer(**footer),
            hk.Embed(
                title=title,
                url=response["siteUrl"],
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .set_thumbnail(response["image"]["large"])
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
        Page (perPage: 5) {
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
        try:
            data = await client.query(
                cls._SEARCH_QUERY,
                {"search": query_, "type": "ANIME"},
            )
        except AniListError:
            return []
        return data.get("Page", {}).get("media", []) or []

    @classmethod
    async def from_id(cls, id_: int, client: AniListClient) -> Optional["ALAnime"]:
        try:
            data = await client.query(cls._FROM_ID_QUERY, {"id": id_, "type": "ANIME"})
        except AniListError:
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
            try:
                data = await self.client.query(
                    self._FROM_ID_QUERY, {"id": self.id, "type": "ANIME"}
                )
            except AniListError:
                return None
            media = data.get("Media")
            if not media:
                return None

        title = media["title"]["english"] or media["title"]["romaji"]
        no_of_items = (
            media["episodes"]
            if media["episodes"] != 1
            else verbose_timedelta(timedelta(minutes=media["duration"]))
        )
        description = (
            self.parse_description(media["description"])
            if media["description"] else "NA"
        )
        studios = media["studios"]["nodes"]

        embed = (
            hk.Embed(
                title=title,
                url=media["siteUrl"],
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Rating", media.get("meanScore", "NA"))
            .add_field("Genres", ", ".join(media["genres"][:4]))
            .add_field("Status", media["status"].replace("_", " "), inline=True)
            .add_field(
                "Episodes" if media["episodes"] != 1 else "Duration",
                no_of_items,
                inline=True,
            )
            .add_field("Studio", studios[0]["name"] if studios else "Unknown", inline=True)
            .add_field("Summary", description)
            .set_thumbnail(media["coverImage"]["large"])
            .set_image(media["bannerImage"])
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        )

        trailer = None
        if media["trailer"]:
            site = media["trailer"]["site"]
            vid = media["trailer"]["id"]
            if site == "youtube":
                trailer = f"https://{site}.com/watch?v={vid}"
            else:
                trailer = f"https://{site}.com/video/{vid}"

        return [embed, trailer]

    # ---- Watch-order (recursive relation walk) ----

    _RELATIONS_QUERY = """
    query ($id: Int, $search: String) {
        Media(id: $id, search: $search, type: ANIME) {
            id
            title { romaji }
            startDate { year month day }
            duration
            episodes
            relations {
                edges {
                    relationType
                    node { id title { romaji } type }
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
        variables = {"id": anime_id} if anime_id else {"search": search}
        return await client.query(cls._RELATIONS_QUERY, variables)

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
        except AniListError:
            return []

        media = data.get("Media")
        if not media:
            return []

        entries = [
            AnimeNode(
                media["id"],
                media["title"]["romaji"],
                media["startDate"],
                media.get("duration", 0),
                media.get("episodes", 1),
            )
        ]

        for edge in (media.get("relations") or {}).get("edges", []):
            node = edge["node"]
            if node["type"] == "ANIME" and edge["relationType"] in (
                "PREQUEL",
                "SEQUEL",
                "SIDE_STORY",
            ):
                entries.extend(
                    await cls.get_complete_series(client, node["id"], visited)
                )

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
        data = await client.query(cls._TRENDS_MEDIA_QUERY, {"search": search_query})
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
        try:
            data = await client.query(
                cls._SEARCH_QUERY,
                {"search": query_, "type": "MANGA"},
            )
        except AniListError:
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
        try:
            data = await client.query(
                cls._URL_FROM_MAL_QUERY,
                {"mal_id": mal_id, "search": name},
            )
        except AniListError:
            return None
        media = data.get("Media")
        return media["siteUrl"] if media else None


class ALNovel(AnilistBase):
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
    async def from_search(cls, query_: str, client: AniListClient) -> Optional[dict]:
        try:
            data = await client.query(
                cls._FROM_SEARCH_QUERY,
                {"search": query_, "type": "MANGA"},
            )
        except AniListError:
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
    query ($search: String, $sort: [MediaSort]) {
        Studio(search: $search) {
            name
            siteUrl
            id
            favourites
            media(sort: $sort) {
                nodes {
                    title { english romaji }
                    coverImage { large }
                    averageScore
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
    async def from_search(cls, query_: str, client: AniListClient) -> Optional[dict]:
        try:
            data = await client.query(
                cls._QUERY,
                {"search": query_, "sort": "FAVOURITES_DESC"},
            )
        except AniListError:
            return None
        return data.get("Studio")


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
        cls, query_: str, client: AniListClient, per_page: int = 10
    ) -> Optional[dict]:
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
            return None
        return data.get("Staff")
