"""Adapter normalizing MyAnimeList / Jikan v4 REST responses into AniList schema dictionaries.

This layer ensures that downstream commands (extensions/adata.py, utils/anilist.py,
utils/components.py) can consume MAL/Jikan data transparently without requiring
rewrites of the UI or embed building code.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, List, Optional, Tuple

FALLBACK_SOURCE_TEXT = os.getenv("MAL_FALLBACK_SOURCE_TEXT", "Source: MyAnimeList.net")
MAL_ICON_URL = os.getenv(
    "MAL_ICON_URL",
    "https://cdn.myanimelist.net/img/sp/icon/apple-touch-icon-256.png",
)


def parse_duration_minutes(duration_str: Optional[str]) -> Optional[int]:
    """Parse minutes from duration strings like '24 min per ep' or '1 hr 45 min'."""
    if not duration_str:
        return None

    total_minutes = 0
    hr_match = re.search(r"(\d+)\s*hr", duration_str, re.IGNORECASE)
    min_match = re.search(r"(\d+)\s*min", duration_str, re.IGNORECASE)

    if hr_match:
        total_minutes += int(hr_match.group(1)) * 60
    if min_match:
        total_minutes += int(min_match.group(1))

    return total_minutes if total_minutes > 0 else None


def parse_iso_date(date_str: Optional[str]) -> Optional[dict]:
    """Parse ISO8601 date string into {year, month, day}."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return {"year": dt.year, "month": dt.month, "day": dt.day}
    except Exception:
        return None


def parse_character_about(
    about_text: Optional[str],
) -> Tuple[Optional[str], Optional[dict], str]:
    """Extract gender, dateOfBirth {year, month, day}, and cleaned bio from character about."""
    if not about_text:
        return None, None, "-"

    gender = None
    dob = None

    gender_match = re.search(r"\bGender:\s*([A-Za-z]+)", about_text, re.IGNORECASE)
    if gender_match:
        gender = gender_match.group(1).capitalize()

    bday_match = re.search(r"\bBirthday:\s*([A-Za-z]+)\s+(\d{1,2})", about_text, re.IGNORECASE)
    if bday_match:
        month_name, day_str = bday_match.group(1), bday_match.group(2)
        try:
            m_dt = datetime.strptime(month_name[:3], "%b")
            dob = {"year": None, "month": m_dt.month, "day": int(day_str)}
        except Exception:
            pass

    return gender, dob, about_text


def extract_primary_va(voices: List[dict]) -> str:
    """Extract Japanese voice actor from MAL/Jikan character voices list."""
    if not voices:
        return "NA"

    ja_voices = [v for v in voices if (v.get("language") or "").lower() == "japanese"]
    selected = ja_voices[0] if ja_voices else voices[0]
    person = selected.get("person") or {}
    name = person.get("name")
    url = person.get("url")

    if name and url:
        return f"[{name}]({url})"
    elif name:
        return name
    return "NA"


class MalAdapter:
    @staticmethod
    def normalize_anime(item: dict) -> dict:
        """Normalize MAL anime item into AniList Media shape."""
        mal_id = item.get("mal_id")
        title_default = item.get("title") or "Unknown"
        title_english = item.get("title_english") or title_default

        episodes = item.get("episodes")
        duration = parse_duration_minutes(item.get("duration"))

        score = item.get("score")
        mean_score = int(round(score * 10)) if score is not None else None

        genres = [g["name"] for g in item.get("genres", []) if isinstance(g, dict) and "name" in g]
        studios = [s["name"] for s in item.get("studios", []) if isinstance(s, dict) and "name" in s]

        images = item.get("images", {}).get("jpg", {})
        large_image = images.get("large_image_url") or images.get("image_url")

        trailer_raw = item.get("trailer", {}) or {}
        youtube_id = trailer_raw.get("youtube_id")
        trailer = {"site": "youtube", "id": youtube_id} if youtube_id else None

        aired = item.get("aired", {}) or {}
        aired_prop = aired.get("prop", {}) or {}
        from_year = aired_prop.get("from", {}).get("year")
        year = item.get("year") or from_year

        status_raw = item.get("status", "")
        if "airing" in status_raw.lower() and "finished" not in status_raw.lower():
            status = "RELEASING"
        elif "finished" in status_raw.lower():
            status = "FINISHED"
        elif "not yet" in status_raw.lower():
            status = "NOT_YET_RELEASED"
        else:
            status = status_raw.replace(" ", "_").upper() or "UNKNOWN"

        return {
            "id": mal_id,
            "idMal": mal_id,
            "title": {
                "english": title_english,
                "romaji": title_default,
            },
            "episodes": episodes,
            "duration": duration or 24,
            "nextAiringEpisode": None,
            "description": item.get("synopsis") or "",
            "startDate": {"year": year},
            "meanScore": mean_score,
            "averageScore": mean_score,
            "genres": genres,
            "status": status,
            "studios": {"nodes": [{"name": name} for name in studios]},
            "coverImage": {"large": large_image},
            "bannerImage": None,
            "trailer": trailer,
            "siteUrl": item.get("url") or f"https://myanimelist.net/anime/{mal_id}",
            "_source": FALLBACK_SOURCE_TEXT,
            "_source_icon": MAL_ICON_URL,
            "_is_fallback": True,
        }

    @staticmethod
    def normalize_manga(item: dict, is_novel: bool = False) -> dict:
        """Normalize MAL manga item into AniList Media shape."""
        mal_id = item.get("mal_id")
        title_default = item.get("title") or "Unknown"
        title_english = item.get("title_english") or title_default

        chapters = item.get("chapters")
        volumes = item.get("volumes")

        score = item.get("score")
        mean_score = int(round(score * 10)) if score is not None else None

        genres = [g["name"] for g in item.get("genres", []) if isinstance(g, dict) and "name" in g]

        images = item.get("images", {}).get("jpg", {})
        large_image = images.get("large_image_url") or images.get("image_url")

        published = item.get("published", {}) or {}
        from_year = published.get("prop", {}).get("from", {}).get("year")

        status_raw = item.get("status", "")
        if "publishing" in status_raw.lower() or "releasing" in status_raw.lower():
            status = "RELEASING"
        elif "finished" in status_raw.lower():
            status = "FINISHED"
        else:
            status = status_raw.replace(" ", "_").upper() or "UNKNOWN"

        return {
            "id": mal_id,
            "idMal": mal_id,
            "title": {
                "english": title_english,
                "romaji": title_default,
            },
            "chapters": chapters,
            "volumes": volumes,
            "episodes": None,
            "description": item.get("synopsis") or "",
            "startDate": {"year": from_year},
            "meanScore": mean_score,
            "averageScore": mean_score,
            "genres": genres,
            "status": status,
            "coverImage": {"large": large_image},
            "bannerImage": None,
            "format": "NOVEL" if is_novel else "MANGA",
            "siteUrl": item.get("url") or f"https://myanimelist.net/manga/{mal_id}",
            "_source": FALLBACK_SOURCE_TEXT,
            "_source_icon": MAL_ICON_URL,
            "_is_fallback": True,
        }

    @staticmethod
    def normalize_character(item: dict) -> dict:
        """Normalize MAL character item into AniList Character shape."""
        mal_id = item.get("mal_id")
        name = item.get("name") or "Unknown"
        nicknames = item.get("nicknames") or []

        images = item.get("images", {}).get("jpg", {})
        large_image = images.get("image_url")

        about = item.get("about") or ""
        gender, dob, _ = parse_character_about(about)

        anime_nodes = []
        for anime_entry in item.get("anime", []) or []:
            anime_info = anime_entry.get("anime", {}) or {}
            title = anime_info.get("title")
            if title:
                anime_nodes.append({"title": {"romaji": title, "english": title}})

        voices = item.get("voices", []) or []

        return {
            "id": mal_id,
            "name": {
                "full": name,
                "alternative": nicknames,
            },
            "favourites": item.get("favorites", 0),
            "description": about,
            "image": {"large": large_image},
            "gender": gender or "Unknown",
            "dateOfBirth": dob or {"year": None, "month": None, "day": None},
            "media": {"nodes": anime_nodes},
            "voices": voices,
            "siteUrl": item.get("url") or f"https://myanimelist.net/character/{mal_id}",
            "_source": FALLBACK_SOURCE_TEXT,
            "_source_icon": MAL_ICON_URL,
            "_is_fallback": True,
        }

    @staticmethod
    def normalize_staff(item: dict) -> dict:
        """Normalize MAL person item into AniList Staff shape."""
        mal_id = item.get("mal_id")
        name = item.get("name") or "Unknown"

        images = item.get("images", {}).get("jpg", {})
        medium_image = images.get("image_url")

        dob = parse_iso_date(item.get("birthday"))

        characters_nodes = []
        for v in (item.get("voices") or [])[:20]:
            char_info = v.get("character") or {}
            anime_info = v.get("anime") or {}
            char_images = char_info.get("images", {}).get("jpg", {})

            characters_nodes.append({
                "name": {"full": char_info.get("name", "Unknown")},
                "favourites": 0,
                "image": {"medium": char_images.get("image_url")},
                "media": {
                    "nodes": [
                        {
                            "title": {
                                "english": anime_info.get("title", "Unknown"),
                                "romaji": anime_info.get("title", "Unknown"),
                            },
                            "type": "ANIME",
                            "favourites": 0,
                        }
                    ]
                },
            })

        return {
            "id": mal_id,
            "name": {"full": name},
            "image": {"medium": medium_image},
            "dateOfBirth": dob or {"year": None, "month": None, "day": None},
            "age": None,
            "gender": None,
            "yearsActive": None,
            "favourites": item.get("favorites", 0),
            "description": item.get("about") or "",
            "siteUrl": item.get("url") or f"https://myanimelist.net/people/{mal_id}",
            "characters": {"nodes": characters_nodes},
            "_source": FALLBACK_SOURCE_TEXT,
            "_source_icon": MAL_ICON_URL,
            "_is_fallback": True,
        }

    @staticmethod
    def normalize_studio(producer: dict, anime_list: List[dict]) -> dict:
        """Normalize MAL producer into AniList Studio shape."""
        mal_id = producer.get("mal_id")
        titles = producer.get("titles") or []
        name = titles[0].get("title") if titles else producer.get("name", "Unknown")

        media_nodes = []
        for anime in anime_list:
            media_nodes.append(MalAdapter.normalize_anime(anime))

        return {
            "id": mal_id,
            "name": name,
            "favourites": producer.get("favorites", 0),
            "siteUrl": producer.get("url") or f"https://myanimelist.net/anime/producer/{mal_id}",
            "media_nodes": media_nodes,
            "_source": FALLBACK_SOURCE_TEXT,
            "_source_icon": MAL_ICON_URL,
            "_is_fallback": True,
        }
