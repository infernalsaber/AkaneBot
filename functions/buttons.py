"""Commonly used functions to ease utility"""
import io
from typing import Literal, Union, Optional
import requests
from PIL import Image
# from bs4 import BeautifulSoup


import hikari as hk
from miru.ext import nav
import miru


def preview_maker(base_url, data_id, title, manga_id, cover):
    req = requests.get(f"{base_url}/at-home/server/{data_id}", timeout=10)
    if not req.ok:
        return

    r_json = req.json()
    pages = []

    for page in r_json["chapter"]["data"]:
        pages.append(
            hk.Embed(title=title, color=0xFF6740)
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
    # buttons = [
    #     nav.PrevButton(
    #         style=hk.ButtonStyle.SECONDARY,
    #         emoji=hk.Emoji.parse("<:pink_arrow_left:1059905106075725955>"),
    #     ),
    #     nav.IndicatorButton(),
    #     nav.NextButton(
    #         style=hk.ButtonStyle.SECONDARY,
    #         emoji=hk.Emoji.parse("<:pink_arrow_right:1059900771816189953>"),
    #     ),
    # ]
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
                flags = hk.MessageFlag.EPHEMERAL
            )
            return
        # await ctx.respond("This is the only correct answer.", flags=hk.MessageFlag.EPHEMERAL)
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
                flags = hk.MessageFlag.EPHEMERAL
            )
            return
        # await ctx.respond("This is the only correct answer.", flags=hk.MessageFlag.EPHEMERAL)
        await ctx.bot.rest.edit_message(
            ctx.channel_id, ctx.message, flags=hk.MessageFlag.SUPPRESS_EMBEDS, components=[]
        )
        self.view.stop()

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
        # if custom_id:
        #     page = self.custom_id
        #     self.view.current_page = int(page)

    async def callback(self, ctx: miru.ViewContext):
        if not ctx.author.id == self.view.user_id:
            await ctx.respond(
                (
                    "You can't interact with this button as " 
                    "you are not the invoker of the command."
                ),
                flags = hk.MessageFlag.EPHEMERAL
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
                flags = hk.MessageFlag.EPHEMERAL
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
        url: Optional[str] = None
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row, url=url
        )

    async def callback(self, ctx: miru.ViewContext):
        ...
        # if self.view.current_page == len(self.view.pages) - 1:
        #     self.view.current_page = 0
        # else:
        #     self.view.current_page += 1
        # await self.view.send_page(ctx)

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
            await self.view.swap_pages(ctx, ctx.bot.d.chapter_info[self.view.message_id][5])
            self.label = "Preview"
            self.emoji = hk.Emoji.parse("<a:peek:1061709886712455308>")
            print(self.view.children)
            for item in self.view.children:

                if not item == self:
                    self.view.remove_item(item)
            view = self.view
            self.view.clear_items()
            view.add_item(self)
            await ctx.edit_response(components=view)


            print("Items removed")
            return
        # await ctx.respond("Testx")
        # view = self.view
        # self.view.clear_items()
        # try:
        #     print("MID: ", self.view.message_id)
        # except:
        #     pass
        # print(data)
        try:
            data = ctx.bot.d.chapter_info[self.view.message_id]
            await self.view.swap_pages(ctx, preview_maker(
                data[0], data[1], data[2], data[3], data[4]
                )
            )
        except:
            await ctx.respond(
                (
                    f"Looks like MD doesn't have this series " 
                    f"{hk.Emoji.parse('<a:AkaneBow:1109245003823317052>')}"
                    f"\nThat or some unknown error."
                ),
                flags = hk.MessageFlag.EPHEMERAL
            )
            return

        self.view.add_item(CustomPrevButton(
            style=hk.ButtonStyle.SECONDARY,
            emoji=hk.Emoji.parse("<:pink_arrow_left:1059905106075725955>"),
            )
        )
        self.view.add_item(nav.IndicatorButton())
        self.view.add_item(CustomNextButton(
            style=hk.ButtonStyle.SECONDARY,
            emoji=hk.Emoji.parse("<:pink_arrow_right:1059900771816189953>"),
            )
        )
        self.view.add_item(NavLinkButton(
            url=f"https://mangadex.org/title/{data[3]}"
            )
        )
        self.label = "🔍"
        self.emoji = None
        await ctx.edit_response(components=self.view)
        # self.view.add_item(

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
        other_page: Union[hk.Embed, str] = None
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
                flags = hk.MessageFlag.EPHEMERAL
            )
            return

        if self.label == "🔍":
            await self.view.swap_pages(ctx, self.other_page)
            self.label = "Trailer"
            self.emoji = hk.Emoji.parse("<a:youtube:1074307805235920896>")
  
            await ctx.edit_response(components=self.view)


            # print("Items removed")
            return
        # await ctx.respond("Testx")
        # view = self.view
        # self.view.clear_items()
        # try:
        #     print("MID: ", self.view.message_id)
        # except:
        #     pass
        # data = ctx.bot.d.chapter_info[self.view.message_id]
        # print(data)
        # try:
        await self.view.swap_pages(ctx, [self.trailer])


        self.label = "🔍"
        self.emoji = None
        await ctx.edit_response(components=self.view)
        # self.view.add_item(

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
        # await ctx.respond("This is the only correct answer.", flags=hk.MessageFlag.EPHEMERAL)
        # await ctx.bot.rest.edit_message(
        #     ctx.channel_id, ctx.message, flags=hk.MessageFlag.SUPPRESS_EMBEDS
        # )
        self.view.stop()
