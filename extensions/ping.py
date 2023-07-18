"""Plugin running the background tasks and utilities for the bot"""
import datetime

import hikari as hk
import lightbulb as lb

ping_plugin = lb.Plugin("Ping", "Pong")


"""Commonly used functions to ease utility"""
from typing import Optional, Union

import hikari as hk
import miru
from miru.ext import nav


async def preview_maker(base_url, data_id, title, manga_id, cover):
    req = await ping_plugin.bot.d.aio_session.get(
        f"{base_url}/at-home/server/{data_id}", timeout=10
    )

    if not req.ok:
        return

    r_json = await req.json()
    pages = []

    try:
        if (
            await ping_plugin.bot.d.aio_session.get(r_json["chapter"]["dataSaver"][0])
        ).ok:
            print("OK\n\n\n")
        else:
            print("NOTOK\n\n\n")
    except Exception as e:
        print("ERra\n\n\n", e)

    for page in r_json["chapter"]["data"]:
        pages.append(
            hk.Embed(
                title=title,
                color=0xFF6740,
                url=f"https://mangadex.org/title/{manga_id}",
            )
            .set_image(f"{r_json['baseUrl']}/data/{r_json['chapter']['hash']}/{page}")
            .set_footer(
                "Fetched via: MangaDex",
                icon="https://avatars.githubusercontent.com/u/100574686?s=280&v=4",
            )
        )
    # Kill the process if there are no pages
    if len(pages) == 0:
        return
    pages.append(
        hk.Embed(title=title, url=f"https://cubari.moe/read/mangadex/{manga_id}/2/1")
        .set_image(cover)
        .set_author(
            name="Click here to continue reading",
            url=f"https://cubari.moe/read/mangadex/{manga_id}/2/1",
        )
    )

    return pages


class GenericButton(miru.Button):
    """A custom next general class"""

    # Let's leave our arguments dynamic this time, instead of hard-coding them
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.ViewContext) -> None:
        if not ctx.author.id == self.view.user_id:
            await ctx.respond(
                (
                    "You can't interact with this button as "
                    "you are not the invoker of the command."
                ),
                flags=hk.MessageFlag.EPHEMERAL,
            )
            return

        self.view.answer = self.label
        self.view.stop()


class KillNavButton(nav.NavButton):
    """A custom next kill class"""

    # Let's leave our arguments dynamic this time, instead of hard-coding them
    def __init__(
        self,
        *,
        style: Union[hk.ButtonStyle, int] = hk.ButtonStyle.DANGER,
        label: Optional[str] = "❌",
        custom_id: Optional[str] = None,
        emoji: Union[hk.Emoji, str, None] = None,
        row: Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        if not ctx.author.id == self.view.user_id:
            await ctx.respond(
                (
                    "You can't interact with this button as "
                    "you are not the invoker of the command."
                ),
                flags=hk.MessageFlag.EPHEMERAL,
            )
            return

        await self.view.message.delete()

    async def before_page_change(self) -> None:
        ...


class CustomPrevButton(nav.NavButton):
    """A custom previous button class"""

    def __init__(
        self,
        *,
        style: Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: Optional[str] = None,
        custom_id: Optional[str] = None,
        emoji: Union[hk.Emoji, str, None] = hk.Emoji.parse(
            "<:pink_arrow_left:1059905106075725955>"
        ),
        row: Optional[int] = None,
        page_no: Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        if not ctx.author.id == self.view.user_id:
            await ctx.respond(
                (
                    "You can't interact with this button as "
                    "you are not the invoker of the command."
                ),
                flags=hk.MessageFlag.EPHEMERAL,
            )
            return
        if self.view.current_page == 0:
            self.view.current_page = len(self.view.pages) - 1
        else:
            self.view.current_page -= 1
        await self.view.send_page(ctx)

    async def before_page_change(self) -> None:
        ...


class CustomNextButton(nav.NavButton):
    """A custom next button class"""

    def __init__(
        self,
        *,
        style: Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: Optional[str] = None,
        custom_id: Optional[str] = None,
        emoji: Union[hk.Emoji, str, None] = hk.Emoji.parse(
            "<:pink_arrow_right:1059900771816189953>"
        ),
        row: Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        if not ctx.author.id == self.view.user_id:
            await ctx.respond(
                (
                    "You can't interact with this button as "
                    "you are not the invoker of the command."
                ),
                flags=hk.MessageFlag.EPHEMERAL,
            )
            return
        if self.view.current_page == len(self.view.pages) - 1:
            self.view.current_page = 0
        else:
            self.view.current_page += 1
        await self.view.send_page(ctx)

    async def before_page_change(self) -> None:
        ...


class NavLinkButton(nav.NavButton):
    """A custom next button class"""

    def __init__(
        self,
        *,
        style: Union[hk.ButtonStyle, int] = hk.ButtonStyle.LINK,
        label: Optional[str] = "🔗",
        custom_id: Optional[str] = None,
        emoji: Union[hk.Emoji, str, None] = None,
        row: Optional[int] = None,
        url: Optional[str] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row, url=url
        )

    async def callback(self, ctx: miru.ViewContext):
        ...

    async def before_page_change(self) -> None:
        ...


class PreviewButton(nav.NavButton):
    """A custom next button class"""

    def __init__(
        self,
        *,
        style: Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: Optional[str] = "Preview",
        custom_id: Optional[str] = None,
        emoji: Union[hk.Emoji, str, None] = hk.Emoji.parse(
            "<a:peek:1061709886712455308>"
        ),
        row: Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        if self.label == "🔍":
            self.label = "Preview"
            self.emoji = hk.Emoji.parse("<a:peek:1061709886712455308>")
            print(self.view.children)
            for item in self.view.children:
                if not item == self:
                    self.view.remove_item(item)
            view = self.view
            self.view.clear_items()
            view.add_item(self)
            view.add_item(KillNavButton())
            await self.view.swap_pages(
                ctx, ctx.bot.d.chapter_info[self.view.message_id][5]
            )

            return

        try:
            for item in self.view.children:
                if not item == self:
                    self.view.remove_item(item)
            data = ctx.bot.d.chapter_info[self.view.message_id]
            await self.view.swap_pages(
                ctx, await preview_maker(data[0], data[1], data[2], data[3], data[4])
            )
        except:
            await ctx.respond(
                (
                    f"Looks like MangaDex doesn't have this series "
                    f"{hk.Emoji.parse('<a:AkaneBow:1109245003823317052>')}"
                    f"\nThat or some unknown error."
                ),
                flags=hk.MessageFlag.EPHEMERAL,
            )
            return

        self.view.add_item(
            CustomPrevButton(
                style=hk.ButtonStyle.SECONDARY,
                emoji=hk.Emoji.parse("<:pink_arrow_left:1059905106075725955>"),
            )
        )
        self.view.add_item(nav.IndicatorButton())
        self.view.add_item(
            CustomNextButton(
                style=hk.ButtonStyle.SECONDARY,
                emoji=hk.Emoji.parse("<:pink_arrow_right:1059900771816189953>"),
            )
        )

        self.view.add_item(KillNavButton())
        self.label = "🔍"
        self.emoji = None
        await ctx.edit_response(components=self.view)

    async def before_page_change(self) -> None:
        ...

    async def on_timeout(self, ctx: miru.ViewContext) -> None:
        await ctx.edit_response(components=[])


class TrailerButton(nav.NavButton):
    """A custom next button class"""

    def __init__(
        self,
        *,
        style: Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: Optional[str] = "Trailer",
        custom_id: Optional[str] = None,
        emoji: Union[hk.Emoji, str, None] = hk.Emoji.parse(
            "<a:youtube:1074307805235920896>"
        ),
        row: Optional[int] = None,
        trailer: str = None,
        other_page: Union[hk.Embed, str] = None,
    ):
        self.trailer = trailer
        self.other_page = other_page
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        if not ctx.author.id == self.view.user_id:
            await ctx.respond(
                (
                    "You can't interact with this button as "
                    "you are not the invoker of the command."
                ),
                flags=hk.MessageFlag.EPHEMERAL,
            )
            return

        if self.label == "🔍":
            self.label = "Trailer"
            self.emoji = hk.Emoji.parse("<a:youtube:1074307805235920896>")
            await self.view.swap_pages(ctx, self.other_page)

            return

        await self.view.swap_pages(ctx, [self.trailer])

        self.label = "🔍"
        self.emoji = None

        await ctx.edit_response(components=self.view)

    async def before_page_change(self) -> None:
        ...

    async def on_timeout(self, ctx: miru.ViewContext) -> None:
        await ctx.edit_response(components=[])


class KillButton(miru.Button):
    """A custom next kill class"""

    # Let's leave our arguments dynamic this time, instead of hard-coding them
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.ViewContext) -> None:
        if not ctx.author.id == self.view.user_id:
            await ctx.respond(
                (
                    "You can't interact with this button as "
                    "you are not the invoker of the command."
                ),
                flags=hk.MessageFlag.EPHEMERAL,
            )
            return

        await self.view.message.delete()


class NewButton(miru.Button):
    def __init__(
        self,
        style: Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: Optional[str] = None,
        link: str = None,
        emoji: hk.Emoji = None,
        custom_id: Optional[str] = None,
    ) -> None:
        self.link = link
        super().__init__(style=style, label=label, emoji=emoji, custom_id=custom_id)
        print(self.link)

    async def callback(self, ctx: miru.ViewContext) -> None:
        try:
            await ctx.respond(f"{self.link}", flags=hk.MessageFlag.EPHEMERAL)
        except Exception as e:
            print(e)


import datetime
import json
from typing import Optional, Sequence, Union
from urllib.parse import urlparse

import feedparser
import hikari as hk
import miru
from miru.ext import nav


class CustomNavi(nav.NavigatorView):
    def __init__(
        self,
        *,
        pages: Sequence[Union[str, hk.Embed, Sequence[hk.Embed]]],
        buttons: Optional[Sequence[nav.NavButton]] = None,
        timeout: Optional[Union[float, int, datetime.timedelta]] = 180.0,
        user_id: hk.Snowflake = None,
    ) -> None:
        self.user_id = user_id
        super().__init__(pages=pages, buttons=buttons, timeout=timeout)

    async def on_timeout(self) -> None:
        await self.message.edit(components=[])
        if self.get_context(self.message).bot.d.chapter_info[self.message_id]:
            self.get_context(self.message).bot.d.chapter_info[self.message_id] = None
            print("Cleared cache\n\n\n")


class CustomView(miru.View):
    def __init__(
        self,
        *,
        autodefer: bool = True,
        timeout: Optional[Union[float, int, datetime.timedelta]] = 180.0,
        user_id: hk.Snowflake = None,
    ) -> None:
        self.user_id = user_id
        super().__init__(autodefer=autodefer, timeout=timeout)


def check_if_url(link: str) -> bool:
    parsed = urlparse(link)
    if parsed.scheme and parsed.netloc:
        return True
    return False


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


class PeristentViewTest(miru.View):
    def __init__(self) -> None:
        super().__init__(autodefer=True, timeout=None)


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(ping_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(ping_plugin)
