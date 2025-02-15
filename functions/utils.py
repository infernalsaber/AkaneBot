"""Utility functions for the bot"""
import io
import os
import random
import typing as t
from datetime import timedelta
from functools import lru_cache
from urllib.parse import urlparse

import feedparser
import hikari as hk
import isodate
import lightbulb as lb
# if t.TYPE_CHECKING:
from aiohttp_client_cache import CachedSession
from bs4 import BeautifulSoup
from ciso8601 import parse_datetime
from orjson import dumps


async def poor_mans_proxy(link: str, session: CachedSession) -> io.BytesIO:
    """Get the bytes from an image link

    Args:
        link (str): image link
        session (CachedSession): The session object to make the

    Returns:
        io.BytesIO: The image bytes
    """
    resp = await session.get(link)
    return io.BytesIO(await resp.read())


# Using an optional proxy microservice, based on https://github.com/infernalsaber/Flask-Image-Proxy
PROXY_URL = os.getenv("PROXY_URL")


def proxy_img(img_url: str) -> str:
    """Simple image proxy"""
    return f"{PROXY_URL}/proxy?url={img_url}" if PROXY_URL else img_url


async def dlogger(bot: lb.BotApp, message: str):
    logs_channel = bot.d.config.get("LOGS_CHANNEL")
    if logs_channel:
        if len(message) < 2000:
            await bot.rest.create_message(logs_channel, message)
        else:
            await bot.rest.create_message(logs_channel, hk.Bytes(message.encode(), "error_message.txt"))

@lru_cache(maxsize=3, typed=False)
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
        async with session.head(link) as r:
            if r.headers["content-type"] in ["image/png", "image/jpeg", "image/jpg"]:
                return 1
            if r.headers["content-type"] in ["image/webp", "image/gif"]:
                return 2
            return 0
    except Exception:
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

    return dumps(feedsdict)


def verbose_timedelta(delta: timedelta) -> str:
    """Convert a :obj:`datetime.timedelta` object into a human friendly string

    Args:
        delta (timedelta): The timedelta object

    Returns:
        str: The human readable string
    """
    d = delta.days
    h, s = divmod(delta.seconds, 3600)
    m, s = divmod(s, 60)
    labels = ["day", "hour", "minute", "second"]
    dhms = [f"{i} {lbl}{'s' if i!=1 else ''}" for i, lbl in zip([d, h, m, s], labels)]
    for start in range(len(dhms)):
        if not dhms[start].startswith("0"):
            break
    for end in range(len(dhms) - 1, -1, -1):
        if not dhms[end].startswith("0"):
            break
    return ", ".join(dhms[start : end + 1])


def verbose_date(*args) -> str:
    """To convert represent dates in a more verbose manner

    Args:
        In the form date, month year

    Returns:
        str: The verbose date string
    """
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


def iso_to_timestamp(iso_date: isodate.Duration) -> int:
    """Convert ISO datetime to timestamp"""
    try:
        return int(parse_datetime(iso_date).astimezone().timestamp())
        # return int(
        # datetime.fromisoformat(iso_date[:-1] + "+00:00").astimezone().timestamp()
        # )

    except ValueError:  # Incase the datetime is not in the iso format, return it as is
        return iso_date


async def tenor_link_from_gif(link: str, session: CachedSession):
    """Scrape the tenor GIF url from the page link"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
        }

        async with session.get(link, headers=headers) as response:
            soup = BeautifulSoup(await response.read(), "lxml")

        return soup.find("meta", {"itemprop": "contentUrl"})["content"]

    except Exception as e:
        print(e)
        return link


def humanized_list_join(lst: list, *, conj: t.Optional[str] = "or") -> str:
    """As the name suggests, convert a list into a
    nice string"""
    if not isinstance(lst, list):
        return lst

    if not len(lst):
        return " "

    if len(lst) == 1:
        return lst[0]

    return f"{','.join(lst[:-1])}" f" {conj} {lst[-1]}"


def get_random_quote() -> str:
    """Funny loading messages"""
    return random.choice(
        [
            "Don't we have a job to do?",
            "One, two, three, four. Two, two, three, four...",
            "Whenever you need me, I'll be there.",
            "I hear the voice of fate, speaking my name in humble supplication…",
            "There's something in the Air… Something tells me a new case is brewing.",
            "Now this is what I call 'a moment of solitude'.",
            "Come on, let's get moving. We're not frozen in place, after all.",
            "The case before us... is a strange and unprecedented one indeed.",
        ]
    )
