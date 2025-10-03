import time
import typing
from datetime import datetime
from random import random
from typing import Dict, List, Set, Union
import re

from curl_cffi import requests


class AnimeNode:
    def __init__(
        self, id: int, title: str, date_info: Dict, duration: int = 0, episodes: int = 0
    ):
        self.id = id
        self.title = title
        # Create a datetime object, defaulting to None if date is incomplete
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


def get_anime_relations(anime_id: int) -> dict:
    """Fetch anime relations from AniList API."""
    query = """
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            id
            title {
                romaji
            }
            relations {
                edges {
                    relationType
                    node {
                        id
                        title {
                            romaji
                        }
                    }
                }
            }
            duration
            episodes
        }
    }
    """

    response = requests.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": {"id": anime_id}},
    )
    return response.json()


def build_timeline(anime_id: int, visited: set = None) -> typing.Optional[AnimeNode]:
    """Recursively build the timeline starting from the given anime ID."""
    if visited is None:
        visited = set()

    if anime_id in visited:
        return None

    visited.add(anime_id)
    data = get_anime_relations(anime_id)

    if "errors" in data:
        return None

    media = data["data"]["Media"]
    time = 0
    if media["duration"] and media["episodes"]:
        time = media["duration"] * media["episodes"]

    current = AnimeNode(anime_id, media["title"]["romaji"], time)

    if media["relations"]:
        for edge in media["relations"]["edges"]:
            relation = edge["relationType"]
            related_anime = edge["node"]

            if relation == "PREQUEL":
                prequel = build_timeline(related_anime["id"], visited)
                if prequel:
                    current.prequels.append(prequel)
            elif relation == "SEQUEL":
                sequel = build_timeline(related_anime["id"], visited)
                if sequel:
                    current.sequels.append(sequel)
            elif relation == "SIDE_STORY":
                side = build_timeline(related_anime["id"], visited)
                if side:
                    current.side_stories.append(side)

    return current


def generate_watch_order(root: AnimeNode, include_side_stories: bool = False) -> list:
    """Generate a linear watch order from the timeline tree."""
    if not root:
        return []

    order = []

    # Add prequels first (recursively)
    for prequel in root.prequels:
        order.extend(generate_watch_order(prequel, include_side_stories))

    # Add current anime
    order.append(root)

    # Add side stories after the main entry if requested
    if include_side_stories:
        for side in root.side_stories:
            order.extend(generate_watch_order(side, include_side_stories))

    # Add sequels last (recursively)
    for sequel in root.sequels:
        order.extend(generate_watch_order(sequel, include_side_stories))

    return order


def format_watch_order(anime_id: int, include_side_stories: bool = False) -> str:
    """Format the watch order as a string with arrows between entries."""
    timeline = build_timeline(anime_id)
    if not timeline:
        return "Could not generate watch order"

    order = generate_watch_order(timeline, include_side_stories)
    find_series_name([anime.title.lower() for anime in order])

    return " -> ".join(anime.title for anime in order)


from functions.algorithms import longest_common_substring





def find_series_name(titles, threshold=0.6):
    """Find the most likely series name from a list of titles."""
    if not titles:
        return ""

    # Clean titles first
    cleaned_titles = [clean_title(t) for t in titles]

    title = longest_common_substring(cleaned_titles, threshold)

    # title = longest_common_substring(cleaned_titles, threshold)
    title = re.sub(r"[.,:/]+$", "", title)
    return title


def clean_title(title):
    """Clean title by removing common suffixes/prefixes and special characters."""
    removals = [": The Movie", ": Episode", " Movie", " Season", " Part", " -"]
    cleaned = title
    for r in removals:
        cleaned = cleaned.replace(r, "")
    return cleaned.strip()


def get_anime_data(session, anime_id: int = None, anime: str = None) -> dict:
    """Fetch single anime data from AniList API."""
    query = """
    query ($id: Int, $search: String) {
        Media(id: $id, search: $search, type: ANIME) {
            id
            title {
                romaji
            }
            startDate {
                year
                month
                day
            }
            duration
            episodes
            relations {
                edges {
                    relationType
                    node {
                        id
                        title {
                            romaji
                        }
                        type
                    }
                }
            }
        }
    }
    """

    if anime_id:
        variables = {"id": anime_id}
    else:
        variables = {"search": anime}

    for _ in range(3):
        response = session.post(
            "https://graphql.anilist.co", json={"query": query, "variables": variables}
        )
        if response.ok:
            break
        if response.status_code == 429:
            print(f"Rate limited")
            # time.sleep(int(response.headers.get("Retry-After")))
            break
    else:
        return {"errors": "Failed to fetch data"}
    return response.json()


def get_complete_series(
    session, anime_id: int, visited_ids: Set[int] = None
) -> List[AnimeNode]:
    """Recursively fetch all related anime in the series."""
    if visited_ids is None:
        visited_ids = set()

    if anime_id in visited_ids:
        return []

    visited_ids.add(anime_id)

    # Add delay to respect API rate limits
    time.sleep(random() / 2)

    data = get_anime_data(session, anime_id)
    if "errors" in data:
        return []

    media = data["data"]["Media"]
    entries = []

    # Add current anime
    current_entry = AnimeNode(
        media["id"],
        media["title"]["romaji"],
        media["startDate"],
        media.get("duration", 0),
        media.get("episodes", 1),
    )
    entries.append(current_entry)

    # Recursively get related anime
    if media["relations"]:
        for edge in media["relations"]["edges"]:
            node = edge["node"]
            if node["type"] == "ANIME" and edge["relationType"] in [
                "PREQUEL",
                "SEQUEL",
                "SIDE_STORY",
            ]:  # Only process anime entries
                related_entries = get_complete_series(session, node["id"], visited_ids)
                entries.extend(related_entries)

    return entries


def format_chronological_order(session, anime_id: int) -> List[AnimeNode]:
    """Generate a chronological watch order for the complete anime series."""
    # Get all related entries
    all_entries = get_complete_series(session, anime_id)

    if not all_entries:
        return []

    # Separate dated and undated entries
    dated_entries = [e for e in all_entries if e.date is not None]
    undated_entries = [e for e in all_entries if e.date is None]

    # Sort dated entries by release date
    dated_entries.sort(key=lambda x: x.date)

    # Combine both lists
    all_sorted_entries = dated_entries + undated_entries

    return all_sorted_entries


if __name__ == "__main__":

    session = requests.Session()

    series = "monogatari"
    resp = get_anime_data(session, anime=series)

    anime_id = int(resp["data"]["Media"]["id"])
    wo = format_chronological_order(session, anime_id=anime_id)
    import ipdb

    ipdb.set_trace()
