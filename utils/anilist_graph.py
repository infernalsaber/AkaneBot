"""Pure helpers for the watch-order feature.

Network access lives on `AniListClient`; the classes/functions here are
used to shape the data returned by those methods.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Dict

from utils.algorithms import longest_common_substring


class AnimeNode:
    def __init__(
        self,
        id: int,
        title: str,
        date_info: Dict,
        duration: int = 0,
        episodes: int = 0,
    ):
        self.id = id
        self.title = title
        try:
            year = date_info.get("year", 0)
            month = date_info.get("month", 1)
            day = date_info.get("day", 1)
            if year and month and day:
                self.date = datetime(year, month, day)
            else:
                self.date = None
        except ValueError:
            self.date = None

        self.duration = duration or 0
        self.episodes = episodes or 1

    def __str__(self):
        watch_time = " (NA)"
        if self.episodes and self.duration:
            total_minutes = self.episodes * self.duration
            hours = total_minutes // 60
            minutes = total_minutes % 60
            watch_time = f"({hours}h{minutes}m)"

        url = f"https://anilist.co/anime/{self.id}"
        return f"[{self.title}]({url}) {watch_time}"


def clean_title(title: str) -> str:
    """Strip common suffixes/prefixes so longest-common-substring converges."""
    removals = [": The Movie", ": Episode", " Movie", " Season", " Part", " -"]
    cleaned = title
    for r in removals:
        cleaned = cleaned.replace(r, "")
    return cleaned.strip()


def find_series_name(titles, threshold: float = 0.6) -> str:
    """Guess the shared series name from a list of entry titles."""
    if not titles:
        return ""
    cleaned = [clean_title(t) for t in titles]
    title = longest_common_substring(cleaned, threshold)
    return re.sub(r"[.,:/]+$", "", title)
