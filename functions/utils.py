import json
import random
from datetime import datetime, timedelta
from urllib.parse import urlparse

import feedparser
import hikari as hk
import requests

# if t.TYPE_CHECKING:
from aiohttp_client_cache import CachedSession
from bs4 import BeautifulSoup


def check_if_url(link: str) -> bool:
    """Simple code to see if the given string is a url or not"""
    parsed = urlparse(link)
    if parsed.scheme and parsed.netloc:
        return True
    return False


async def is_image(link: str, session: CachedSession) -> int:
    """Using headers check if a link is of an image or not

    Args:
        link (str): The link to check
        session (CachedSession): The async. (cached or otherwise) session

    Returns:
        int: 0 if not image, 1/2 if yes
    """
    try:
        async with session.head(link, timeout=2) as r:
            if r.headers["content-type"] in ["image/png", "image/jpeg", "image/jpg"]:
                return 1
            if r.headers["content-type"] in ["image/webp", "image/gif"]:
                return 2
            return 0
    except:
        return 0


def rss2json(url):
    """
    rss atom to parsed json data
    supports google alerts
    """

    item = {}
    feedslist = []
    feed = {}
    feedsdict = {}
    # parsed feed url
    parsedurl = feedparser.parse(url)

    # feed meta data
    feed["status"] = "ok"
    feed["version"] = parsedurl.version
    if "updated" in parsedurl.feed.keys():
        feed["date"] = parsedurl.feed.updated
    if "title" in parsedurl.feed.keys():
        feed["title"] = parsedurl.feed.title
    if "image" in parsedurl.feed.keys():
        feed["image"] = parsedurl.feed.image
    feedsdict["data"] = feed

    # feed parsing
    for fd in parsedurl.entries:
        if "title" in fd.keys():
            item["title"] = fd.title

        if "link" in fd.keys():
            item["link"] = fd.link

        if "summary" in fd.keys():
            item["summary"] = fd.summary

        if "published" in fd.keys():
            item["published"] = fd.published

        if "storyimage" in fd.keys():
            item["thumbnail"] = fd.storyimage

        if "media_content" in fd.keys():
            item["thumbnail"] = fd.media_content

        if "tags" in fd.keys():
            if "term" in fd.tags:
                item["keywords"] = fd.tags[0]["term"]

        feedslist.append(item.copy())

    feedsdict["feeds"] = feedslist

    return json.dumps(feedsdict)


def verbose_timedelta(delta: timedelta):
    d = delta.days
    h, s = divmod(delta.seconds, 3600)
    m, s = divmod(s, 60)
    labels = ["day", "hour", "minute", "second"]
    dhms = [
        "%s %s%s" % (i, lbl, "s" if i != 1 else "")
        for i, lbl in zip([d, h, m, s], labels)
    ]
    for start in range(len(dhms)):
        if not dhms[start].startswith("0"):
            break
    for end in range(len(dhms) - 1, -1, -1):
        if not dhms[end].startswith("0"):
            break
    return ", ".join(dhms[start : end + 1])


def verbose_date(*args):
    month_num_map = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }

    day, month, year = args

    verbose_date = " ".join([day, month_num_map[int(month)]])
    verbose_date += f", {year}" if year else ""

    return verbose_date


def iso_to_timestamp(iso_date):
    """Convert ISO datetime to timestamp"""
    try:
        return int(
            datetime.fromisoformat(iso_date[:-1] + "+00:00").astimezone().timestamp()
        )

    except ValueError:  # Incase the datetime is not in the iso format, return it as is
        return iso_date


async def tenor_link_from_gif(link: str, session: CachedSession):
    """Scrape the tenor GIF url from the page link"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
        }

        async with session.get(link, headers=headers, timeout=2) as response:
            soup = BeautifulSoup(await response.read(), "lxml")

        return soup.find("meta", {"itemprop": "contentUrl"})["content"]

    except Exception as e:
        print(e)
        return link


def get_image_dominant_colour(link: str) -> hk.Color:
    """Get the dominant colour of an image from a link to it

    Args:
        link (str): Link to the image

    Returns:
        hk.Color: Dominant Colour
    """

    return hk.Color.of(
        get_dominant_colour(Image.open(requests.get(link, stream=True, timeout=10).raw))
    )


def humanized_list_join(lst) -> str:
    if not isinstance(lst, list) or isinstance(lst, tuple):
        return lst

    if len(lst) == 0:
        return " "

    if len(lst) == 1:
        return lst[0]

    return f"{','.join(lst[:-1])}" f"or {lst[-1]}"


async def get_anitrendz_latest(session: CachedSession):
    try:
        link = "https://anitrendz.tumblr.com/"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
        }

        async with session.get(link, headers=headers, timeout=3) as response:
            soup = BeautifulSoup(await response.read(), "lxml")

        return soup.find("a", {"class": "post_media_photo_anchor"})["data-big-photo"]

    except Exception as e:
        print(e)
        return link


def get_random_quote():
    return random.choice(
        [
            "Don't we have a job to do?",
            "One, two, three, four. Two, two, three, four...",
            "Whenever you need me, I'll be there.",
            "I Hear The Voice Of Fate, Speaking My Name In Humble Supplication…",
            "There's Something In The Air… Something Tells Me A New Case Is Brewing.",
            "Now this is what I call 'a moment of solitude.'",
        ]
    )
