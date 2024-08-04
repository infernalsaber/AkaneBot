"""Custom view classes"""
import typing as t
from datetime import timedelta

import aiohttp_client_cache
import hikari as hk
import miru
from miru.ext import nav

from functions.buttons import CustomNextButton, CustomPrevButton, KillNavButton
from functions.utils import check_if_url


class SelectView(miru.View):
    """A subclassed view designed for Text Select"""

    def __init__(self, user_id: hk.Snowflake, pages: dict[str, hk.Embed]) -> None:
        self.user_id = user_id
        self.pages = pages
        super().__init__(timeout=60 * 60)

    async def view_check(self, ctx: miru.Context) -> bool:
        if ctx.user.id == self.user_id:
            return True
        await ctx.respond(
            (
                "You can't interact with this button as "
                "you are not the invoker of the command."
            ),
            flags=hk.MessageFlag.EPHEMERAL,
        )
        return False


class PeristentViewTest(miru.View):
    """A subclassed view designed to make persistent views(wip)"""

    def __init__(self) -> None:
        super().__init__(autodefer=True, timeout=None)


class AuthorNavi(nav.NavigatorView):
    """A subclassed navigator view with author checks for the view"""

    def __init__(
        self,
        *,
        pages: t.Sequence[t.Union[str, hk.Embed, t.Sequence[hk.Embed]]],
        buttons: t.Optional[t.Sequence[nav.NavButton]] = None,
        timeout: t.Optional[t.Union[float, int, timedelta]] = 5 * 60,
        user_id: t.Optional[hk.Snowflake] = None,
        clean_items: t.Optional[bool] = True,
    ) -> None:
        self.user_id = user_id
        self.clean_items = clean_items
        if not buttons:
            buttons = [
                CustomPrevButton(),
                nav.IndicatorButton(),
                CustomNextButton(),
                KillNavButton(),
            ]
        super().__init__(pages=pages, buttons=buttons, timeout=timeout)

    async def view_check(self, ctx: miru.Context) -> bool:
        if ctx.user.id == self.user_id:
            return True
        await ctx.respond(
            (
                "You can't interact with this button as "
                "you are not the invoker of the command."
            ),
            flags=hk.MessageFlag.EPHEMERAL,
        )
        return False

    async def on_timeout(self) -> None:
        if not self.clean_items:
            return

        if self.message:
            new_view = None
            for item in self.children:
                if item.url is not None:
                    new_view = self.remove_item(item)

            await self.message.edit(components=new_view)


class AuthorView(miru.View):
    """A subclassed view with author checks for the view"""

    def __init__(
        self,
        *,
        autodefer: bool = True,
        timeout: t.Optional[t.Union[float, int, timedelta]] = 5 * 60,
        session: t.Optional[aiohttp_client_cache.CachedSession] = None,
        user_id: t.Optional[hk.Snowflake] = None,
        clean_items: t.Optional[bool] = True,
    ) -> None:
        self.user_id = user_id
        self.session = session
        self.answer = None
        self.clean_items = clean_items
        super().__init__(autodefer=autodefer, timeout=timeout)

    async def on_timeout(self) -> None:
        if not self.clean_items:
            return

        if self.message:
            new_view = None
            for item in self.children:
                if not check_if_url(item.url):
                    new_view = self.remove_item(item)

            await self.message.edit(components=new_view)

    async def view_check(self, ctx: miru.Context) -> bool:
        if ctx.user.id == self.user_id:
            return True
        await ctx.respond(
            (
                "You can't interact with this button as "
                "you are not the invoker of the command."
            ),
            flags=hk.MessageFlag.EPHEMERAL,
        )
        return False


class PreView(nav.NavigatorView):
    """A view designed for the preview feature of the manga command"""

    def __init__(
        self,
        *,
        session: aiohttp_client_cache.CachedSession,
        pages: t.Sequence[t.Union[str, hk.Embed, t.Sequence[hk.Embed]]],
        buttons: t.Optional[t.Sequence[nav.NavButton]] = None,
        timeout: t.Optional[t.Union[float, int, timedelta]] = 180.0,
        user_id: t.Optional[hk.Snowflake] = None,
    ) -> None:
        self.user_id = user_id
        self.session = session

        super().__init__(pages=pages, buttons=buttons, timeout=timeout)

    async def on_timeout(self) -> None:
        # Clearing the memory occupied by the pages
        if self.message.app.d.chapter_info[self.message_id]:
            self.message.app.d.chapter_info[self.message_id] = None

        if self.message:
            await self.message.edit(components=[])

    async def view_check(self, ctx: miru.Context) -> bool:
        if ctx.user.id == self.user_id:
            return True
        await ctx.respond(
            (
                "You can't interact with this button as "
                "you are not the invoker of the command."
            ),
            flags=hk.MessageFlag.EPHEMERAL,
        )
        return False


class TabbedSwitcher(miru.View):
    """A new view which will specialize in switching embeds via buttons"""

    def __init__(
        self,
        *,
        pages: t.Sequence[hk.Embed],
        buttons: t.Sequence[t.Tuple[t.Optional[str], t.Optional[hk.Emoji]]],
        active_style: hk.ButtonStyle,
        normal_style: hk.ButtonStyle,
    ):
        for btn in buttons:
            self.add_item(miru.Button(style=normal_style, label=btn[0], emoji=btn[1]))

        # self._page_btn_map

        super().__init__()


# class TabbedSwitcherButton(nav.NavButton)
