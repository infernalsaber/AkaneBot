"""Custom view classes"""
import typing as t 
import hikari as hk
import miru
from miru.ext import nav

from datetime import timedelta
import aiohttp_client_cache

from functions.buttons import *
from datetime import datetime


class SelectView(miru.View):
    def __init__(self, user_id: hk.Snowflake, pages: t.Collection[hk.Embed]) -> None:
        self.user_id = user_id
        self.pages = pages
        super().__init__(timeout=60*60)

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
    def __init__(self) -> None:
        super().__init__(autodefer=True, timeout=None)


class CustomNavi(nav.NavigatorView):
    def __init__(
        self,
        *,
        pages: t.Sequence[t.Union[str, hk.Embed, t.Sequence[hk.Embed]]],
        buttons: t.Optional[t.Sequence[nav.NavButton]] = None,
        timeout: t.Optional[t.Union[float, int, timedelta]] = 180.0,
        user_id: hk.Snowflake = None,
    ) -> None:

        self.user_id = user_id
        if not buttons:
            buttons = [CustomPrevButton(), nav.IndicatorButton(), CustomNextButton(), KillNavButton()]
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
        await self.message.edit(components=[])

        #Clearing the memory occupied by the preview
        # if self.get_context(self.message).bot.d.chapter_info[self.message_id]:
            # self.get_context(self.message).bot.d.chapter_info[self.message_id] = None


class CustomView(miru.View):
    def __init__(
        self,
        *,
        autodefer: bool = True,
        timeout: t.Optional[t.Union[float, int, timedelta]] = 180.0,
        user_id: hk.Snowflake = None,
    ) -> None:

        self.user_id = user_id
        super().__init__(autodefer=autodefer, timeout=timeout)

    async def on_timeout(self) -> None:
        ...

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
    def __init__(
        self,
        *,
        session: aiohttp_client_cache.CachedSession,
        pages: t.Sequence[t.Union[str, hk.Embed, t.Sequence[hk.Embed]]],
        buttons: t.Optional[t.Sequence[nav.NavButton]] = None,
        timeout: t.Optional[t.Union[float, int, timedelta]] = 180.0,
        user_id: hk.Snowflake = None,
    ) -> None:

        self.user_id = user_id
        self.session = session

        super().__init__(pages=pages, buttons=buttons, timeout=timeout)


    async def on_timeout(self) -> None:
        await self.message.edit(components=[])

        # Clearing the memory occupied by the pages
        if self.get_context(self.message).bot.d.chapter_info[self.message_id]:
            self.get_context(self.message).bot.d.chapter_info[self.message_id] = None

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

# class AutoPaginator(CustomNavi):
#     def __init__(
#         self,
#         *,
#         content: t.Sequence[t.Sequence[str]],
#         pages,
#         # base_embed: t.Optional[hk.Embed] = None,
#         # buttons: t.Optional[t.Sequence[nav.NavButton]] = None,
#         timeout: t.Optional[t.Union[float, int, timedelta]] = 5*60,
#         user_id: hk.Snowflake = None,
#     ) -> None:

#         self.user_id = user_id
#         if not buttons:
#             buttons = [CustomPrevButton(), nav.NavButton(), CustomNextButton(), KillNavButton()]
#         # pages = self._make_pages_from_data(content, base_embed=base_embed)
#         super().__init__(pages=pages, buttons=buttons, timeout=timeout)


#     def _make_pages_from_data(content: t.Sequence[t.Sequence[str]], *, base_embed: t.Optional[hk.Embed] = None) -> t.Sequence[hk.Embed]:
#         if not base_embed:
#             base_embed = hk.Embed(
#                 color=0x43408A,
#                 timestamp=datetime.now().astimezone()
#             )
#         pages: t.Sequence[hk.Embed] = []
#         col1: str = ""
#         col2: str = ""

#         for i, item in enumerate(content):
#             col1 += item[0]
#             col2 += item[1]
#             if i % 19 or len(content-1):
#                 pages.append(
#                     base_embed.add_field("check", col1).add_field("ok", col2)
#                 )
#         return pages
    
#     async def on_timeout(self) -> None:
#         await self.message.edit(components=[])


        