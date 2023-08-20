"""Custom Button classes"""
import io
import typing as t
from typing import Optional

import hikari as hk
import miru
from miru.ext import nav


# from bs4 import BeautifulSoup
async def poor_mans_proxy(link: str, session):
    resp = await session.get(link, timeout=2)
    return io.BytesIO(await resp.read())


async def preview_maker(base_url, data_id, title, manga_id, cover, session):
    """A preview maker function for the manga previews"""

    req = await session.get(f"{base_url}/at-home/server/{data_id}", timeout=10)

    if not req.ok:
        return

    r_json = await req.json()
    pages = []

    try:
        if (await session.get(r_json["chapter"]["dataSaver"][0])).ok:
            print("OK\n\n\n")
        else:
            print("NOTOK\n\n\n")
    except Exception as e:
        print("ERra\n\n\n", e)

    for page in r_json["chapter"]["data"][:5]:
        # Proxy the first five at first
        pages.append(
            hk.Embed(
                title=title,
                color=0xFF6740,
                url=f"https://mangadex.org/title/{manga_id}",
            )
            .set_image(
                await poor_mans_proxy(
                    f"{r_json['baseUrl']}/data/{r_json['chapter']['hash']}/{page}",
                    session,
                )
            )
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
    """A general button class"""

    # Let's leave our arguments dynamic this time, instead of hard-coding them
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.ViewContext) -> None:
        self.view.answer = self.label
        self.view.stop()


class KillNavButton(nav.NavButton):
    """A custom navigator kill button class"""

    def __init__(
        self,
        *,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.DANGER,
        label: t.Optional[str] = "❌",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        await self.view.message.delete()

    async def before_page_change(self) -> None:
        ...


class CustomPrevButton(nav.NavButton):
    """A custom previous button class to make a rotating navigator"""

    def __init__(
        self,
        *,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = None,
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = hk.Emoji.parse(
            "<:pink_arrow_left:1059905106075725955>"
        ),
        row: t.Optional[int] = None,
        page_no: t.Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        if self.view.current_page == 0:
            self.view.current_page = len(self.view.pages) - 1
        else:
            self.view.current_page -= 1
        await self.view.send_page(ctx)

    async def before_page_change(self) -> None:
        ...


class CustomNextButton(nav.NavButton):
    """A custom next button class to make a rotating navigator"""

    def __init__(
        self,
        *,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = None,
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = hk.Emoji.parse(
            "<:pink_arrow_right:1059900771816189953>"
        ),
        row: t.Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        if self.view.current_page == len(self.view.pages) - 1:
            self.view.current_page = 0
        else:
            self.view.current_page += 1
        await self.view.send_page(ctx)

    async def before_page_change(self) -> None:
        ...


class NavButton(nav.NavButton):
    """A custom next button class"""

    def __init__(
        self,
        *,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.LINK,
        label: t.Optional[str] = "🔗",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
        url: t.Optional[str] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row, url=url
        )

    async def callback(self, ctx: miru.ViewContext):
        ...

    async def before_page_change(self) -> None:
        ...


class PreviewButton(nav.NavButton):
    """A custom button for the manga preview"""

    def __init__(
        self,
        *,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = "Preview",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = hk.Emoji.parse(
            "<a:peek:1061709886712455308>"
        ),
        row: t.Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        if self.label == "🔍":
            self.label = "Preview"
            self.emoji = hk.Emoji.parse("<a:peek:1061709886712455308>")

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
            swap_pages = None
            swap_pages = await preview_maker(
                data[0], data[1], data[2], data[3], data[4], self.view.session
            )
            # await self.view.swap_pages(
            #     ctx, )
            # )
        except Exception:
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
        await self.view.swap_pages(ctx, swap_pages)
        # await ctx.edit_response(components=self.view)

    async def before_page_change(self) -> None:
        ...

    async def on_timeout(self, ctx: miru.ViewContext) -> None:
        await ctx.edit_response(components=[])


class TrailerButton(miru.Button):
    """A custom next button class"""

    def __init__(
        self,
        *,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = "Trailer",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = hk.Emoji.parse(
            "<a:youtube:1074307805235920896>"
        ),
        row: t.Optional[int] = None,
        trailer: t.Optional[str] = None,
        other_page: Optional[t.Union[hk.Embed, str]] = None,
    ):
        self.trailer = trailer
        self.other_page = other_page
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        # if not ctx.author.id == self.view.user_id:
        #     await ctx.respond(
        #         (
        #             "You can't interact with this button as "
        #             "you are not the invoker of the command."
        #         ),
        #         flags=hk.MessageFlag.EPHEMERAL,
        #     )
        #     return

        if self.label == "🔍":
            self.label = "Trailer"
            self.emoji = hk.Emoji.parse("<a:youtube:1074307805235920896>")

            await ctx.edit_response(
                content=None, embeds=[self.other_page], components=self.view
            )

            # await self.view.swap_pages(ctx, self.other_page)

            return

        self.label = "🔍"
        self.emoji = None

        await ctx.edit_response(content=self.trailer, embeds=[])
        # await self.view.swap_pages(ctx, [self.trailer])

        await ctx.edit_response(components=self.view)

    async def before_page_change(self) -> None:
        ...


class KillButton(miru.Button):
    """A custom kill button class"""

    def __init__(
        self,
        *,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = "❌",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        await self.view.message.delete()


class NewButton(miru.Button):
    """A spitter button for the releases feed"""

    def __init__(
        self,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = None,
        link: Optional[str] = None,
        emoji: Optional[hk.Emoji] = None,
        custom_id: t.Optional[str] = None,
    ) -> None:
        self.link = link
        super().__init__(style=style, label=label, emoji=emoji, custom_id=custom_id)

    async def callback(self, ctx: miru.ViewContext) -> None:
        try:
            await ctx.respond(f"```{self.link}```", flags=hk.MessageFlag.EPHEMERAL)
        except Exception as e:
            print(e)


class SwapButton(miru.Button):
    """A button to switch between a two-paged view"""

    def __init__(
        self,
        *,
        style: t.Union[hk.ButtonStyle, int] = hk.ButtonStyle.SECONDARY,
        label1: t.Optional[str] = None,
        custom_id: t.Optional[str] = None,
        emoji1: t.Optional[t.Union[hk.Emoji, str]] = None,
        label2: t.Optional[str] = None,
        emoji2: t.Optional[str] = None,
        row: t.Optional[int] = None,
        original_page: Optional[t.Union[hk.Embed, str]] = None,
        swap_page: Optional[t.Union[hk.Embed, str]] = None,
    ):
        self.swap_page = swap_page
        self.original_page = original_page

        self.emoji1 = emoji1
        self.emoji2 = emoji2
        self.label1 = label1
        self.label2 = label2

        super().__init__(
            style=style, label=label1, custom_id=custom_id, emoji=emoji1, row=row
        )

    async def callback(self, ctx: miru.ViewContext):
        if self.emoji == self.emoji1:
            if self.label2 or self.emoji2:
                self.label = self.label2
                self.emoji = self.emoji2

            # Page 1 -> 2

            if isinstance(self.swap_page, str):
                await ctx.edit_response(
                    content=self.swap_page, embeds=[], components=self.view
                )
            else:
                await ctx.edit_response(
                    content=None, embeds=[self.swap_page], components=self.view
                )

            return

        # Page 2 -> 1

        self.label = self.label1
        self.emoji = self.emoji1

        if isinstance(self.original_page, str):
            await ctx.edit_response(
                content=self.original_page, embeds=[], components=self.view
            )
        else:
            await ctx.edit_response(
                content=None, embeds=[self.original_page], components=self.view
            )

    async def before_page_change(self) -> None:
        ...
