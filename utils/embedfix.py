"""Site handlers for embed fixing: each turns a matched link into an embed"""

import asyncio
import json
import re
import typing as t

import hikari as hk
from aiohttp_client_cache import CachedSession
from mloader.loader import MangaLoader

from utils.misc import truncate_words

MANGAPLUS_PATTERN = re.compile(
    r"https?://mangaplus\.shueisha\.co\.jp/(viewer|titles)/(\d+)", re.IGNORECASE
)
MANGAPLUS_ICON = "https://mangaplus.shueisha.co.jp/icn/app_icon_192.png"

MIYOUSHE_PATTERN = re.compile(
    r"https?://(?:www\.)?miyoushe\.com/\w+/article/(\d+)", re.IGNORECASE
)
MIYOUSHE_API = "https://bbs-api.miyoushe.com/post/wapi/getPostFull"
MIYOUSHE_ICON = "https://www.miyoushe.com/_static/img/miHoYo_Game.2457753.png"
MIYOUSHE_HEADERS = {
    "Origin": "https://www.miyoushe.com",
    "Referer": "https://www.miyoushe.com/",
    "User-Agent": "AkaneBot/1.0 (+https://github.com/infernalsaber/AkaneBot)",
}

manga_loader = MangaLoader(exporter=None)


async def mangaplus_embed(
    match: re.Match, session: CachedSession
) -> t.Optional[hk.Embed]:
    """Embed for a MangaPlus chapter (viewer) or series (titles) link"""
    link_type, resource_id = match.groups()

    # mloader is synchronous, so its calls run in a thread
    chapter_line = ""
    title_id = resource_id
    if link_type == "viewer":
        viewer = await asyncio.to_thread(manga_loader._load_pages, resource_id)
        if not viewer.title_id:
            return None
        title_id = viewer.title_id
        chapter_line = f"**{viewer.chapter_name}**\n\n"

    detail = await asyncio.to_thread(manga_loader._get_title_details, title_id)
    if not detail.title.title_id:
        return None

    overview = truncate_words(detail.overview, 200 if chapter_line else 400)
    return (
        hk.Embed(
            title=detail.title.name,
            description=f"{chapter_line}{overview}",
            url=match.group(0),
            color=0xE63946,
        )
        .set_thumbnail(detail.title.portrait_image_url or detail.title_image_url)
        .set_footer("Source: MangaPlus", icon=MANGAPLUS_ICON)
    )


async def miyoushe_embed(
    match: re.Match, session: CachedSession
) -> t.Optional[hk.Embed]:
    """Embed for a Miyoushe post link"""
    async with session.get(
        MIYOUSHE_API, params={"post_id": match.group(1)}, headers=MIYOUSHE_HEADERS
    ) as response:
        data = await response.json()

    post = ((data.get("data") or {}).get("post") or {}).get("post")
    if not post:
        return None

    # Image-only posts have no 'describe' in their content
    description = json.loads(post["content"]).get("describe")
    embed = hk.Embed(
        title=post["subject"],
        description=truncate_words(description, 400) if description else None,
        url=match.group(0),
        color=0x1F2233,
    )
    if post["images"]:
        embed.set_image(post["images"][0])
    return embed.set_footer("Source: Miyoushe", icon=MIYOUSHE_ICON)


HANDLERS = [
    (MANGAPLUS_PATTERN, mangaplus_embed),
    (MIYOUSHE_PATTERN, miyoushe_embed),
]
