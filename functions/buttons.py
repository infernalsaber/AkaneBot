"""Commonly used functions to ease utility"""
import io
from typing import Literal, Union, Optional
import requests
from PIL import Image
from bs4 import BeautifulSoup


import hikari as hk
from miru.ext import nav
import miru

class GenericButton(miru.Button):
    """A custom next general class"""

    # Let's leave our arguments dynamic this time, instead of hard-coding them
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.ViewContext) -> None:
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
        if self.view.current_page == len(self.view.pages) - 1:
            self.view.current_page = 0
        else:
            self.view.current_page += 1
        await self.view.send_page(ctx)

    async def before_page_change(self) -> None:
        ...

