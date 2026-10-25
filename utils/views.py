"""Custom view classes"""
import asyncio
import logging
import typing as t
from datetime import timedelta

import aiohttp_client_cache
import hikari as hk
import miru
from miru.ext import nav

from utils import usercard
from utils.buttons import CustomNextButton, CustomPrevButton, KillButton, KillNavButton
from utils.components import UserCardSelect
from utils.misc import check_if_url
from utils.models import EmoteCollection as emotes


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
        timeout: t.Optional[t.Union[float, int, timedelta]] = 15 * 60,
        user_id: t.Optional[hk.Snowflake] = None,
        clean_items: t.Optional[bool] = True,
    ) -> None:
        self.user_id = user_id
        self.clean_items = clean_items
        if buttons == "default":
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
        timeout: t.Optional[t.Union[float, int, timedelta]] = 15 * 60,
        session: t.Optional[aiohttp_client_cache.CachedSession] = None,
        user_id: t.Optional[hk.Snowflake] = None,
        clean_items: t.Optional[bool] = True,
        is_fallback: bool = False,
        provider: t.Optional[str] = None,
    ) -> None:
        self.user_id = user_id
        self.session = session
        self.is_fallback = is_fallback
        self.provider = provider or ("mal" if is_fallback else "anilist")
        self.answer = None
        self.clean_items = clean_items
        super().__init__(autodefer=autodefer, timeout=timeout)

    async def on_timeout(self) -> None:
        if not self.clean_items:
            return

        if self.message:
            new_view = None
            for item in self.children:
                if not hasattr(item, "url") or not check_if_url(item.url):
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


class SelectView(AuthorView):
    """A subclassed view designed for Text Select"""

    def __init__(
        self,
        user_id: hk.Snowflake,
        pages: dict[str, hk.Embed],
        is_fallback: bool = False,
        provider: t.Optional[str] = None,
    ) -> None:
        self.pages = pages
        super().__init__(
            timeout=60 * 60,
            clean_items=False,
            user_id=user_id,
            is_fallback=is_fallback,
            provider=provider,
        )


class UserCardView(AuthorView):
    """A view switching between an AL user's About, Favourites and Friends cards

    Skeletons (no images) are shown right away and replaced by the full cards
    as they finish rendering in the background.
    """

    def __init__(self, user_id: hk.Snowflake, session, user: dict) -> None:
        super().__init__(user_id=user_id, session=session)
        self.user = user
        self.current = "about"
        self.cards: dict[str, bytes] = {}
        self._tasks: set[asyncio.Task] = set()  # keeps the background renders alive

        self.add_item(UserCardSelect())
        self.add_item(
            miru.Button(
                style=hk.ButtonStyle.LINK,
                url=f"https://anilist.co/user/{user['name']}",
                label="Profile",
                emoji=hk.Emoji.parse(emotes.AL.value),
            )
        )
        self.add_item(KillButton())

    def card(self, kind: str) -> hk.Bytes:
        return hk.Bytes(self.cards[kind], f"{kind}.png")

    async def render_skeletons(self) -> None:
        for kind in usercard.KINDS:
            self.cards[kind] = await usercard.render_skeleton(kind, self.user)

    def render_in_background(self) -> None:
        for kind in usercard.KINDS:
            task = asyncio.create_task(self._render(kind))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _render(self, kind: str) -> None:
        try:
            self.cards[kind] = await usercard.render_card(kind, self.user, self.session)
        except Exception:
            logging.exception(f"Failed to render {kind} card for {self.user['name']}")
            return  # the skeleton stays up

        if kind == self.current and self.message:
            try:
                await self.message.edit(attachment=self.card(kind), components=self)
            except hk.HTTPError:
                pass  # message deleted or not editable anymore


class SelectNavigator(AuthorNavi):
    """A subclassed view designed for Text Select"""

    def __init__(
        self,
        user_id: hk.Snowflake,
        dropdown_options: dict[str, hk.Embed],
        dropdown_components,
        first_page,
    ) -> None:
        self.dropdown_options = dropdown_options
        self.dropdown_components = dropdown_components
        super().__init__(
            timeout=60 * 60,
            clean_items=False,
            user_id=user_id,
            pages=dropdown_options[first_page],
            buttons=dropdown_components[first_page],
        )


class PreView(nav.NavigatorView):
    """A view designed for the preview feature of the manga command"""

    def __init__(
        self,
        *,
        session: aiohttp_client_cache.CachedSession,
        pages: t.Sequence[t.Union[str, hk.Embed, t.Sequence[hk.Embed]]],
        buttons: t.Optional[t.Sequence[nav.NavButton]] = None,
        timeout: t.Optional[t.Union[float, int, timedelta]] = 15 * 60,
        user_id: t.Optional[hk.Snowflake] = None,
    ) -> None:
        self.user_id = user_id
        self.session = session

        super().__init__(pages=pages, buttons=buttons, timeout=timeout)

    async def on_timeout(self) -> None:
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
