"""Custom Button classes"""
import typing as t

import hikari as hk
import miru
from miru.ext import nav

from functions.models import ColorPalette as colors
from functions.models import EmoteCollection as emotes
from functions.utils import proxy_img

# from functions.views import AuthorView

# from bs4 import BeautifulSoup


async def preview_maker(
    base_url, data_id, title, manga_id, cover, session
) -> t.Union[list[hk.Embed], None]:
    """A preview maker function for the manga previews"""

    req = await session.get(f"{base_url}/at-home/server/{data_id}", timeout=10)

    if not req.ok:
        return None

    r_json = await req.json()
    pages = []

    for page in r_json["chapter"]["dataSaver"]:
        pages.append(
            hk.Embed(
                title=title,
                color=colors.MANGADEX,
                url=f"https://mangadex.org/title/{manga_id}",
            )
            .set_image(
                proxy_img(
                    f"{r_json['baseUrl']}/data-saver/{r_json['chapter']['hash']}/{page}"
                )
            )
            .set_footer(
                "Fetched via: MangaDex",
                icon="https://avatars.githubusercontent.com/u/100574686?s=280&v=4",
            )
        )
    # Kill the process if there are no pages
    if not pages:
        return None
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
    """A general button class, value only works only with AuthorView"""

    # Let's leave our arguments dynamic this time, instead of hard-coding them
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.ViewContext) -> None:
        if self.label:
            self.view.answer = self.label
            self.view.stop()
        # else:
        # await ctx.respond("Nope", ephemeral=True)


class KillNavButton(nav.NavButton):
    """A custom navigator kill button class"""

    def __init__(
        self,
        *,
        style: hk.ButtonStyle = hk.ButtonStyle.DANGER,
        label: t.Optional[str] = "❌",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        if self.view.message:
            await self.view.message.delete()

    async def before_page_change(self) -> None:
        ...


class CustomPrevButton(nav.NavButton):
    """A custom previous button class to make a rotating navigator"""

    def __init__(
        self,
        *,
        style: hk.ButtonStyle = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = None,
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
    ):
        if not emoji:
            emoji = hk.Emoji.parse(emotes.PREVIOUS.value)

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
        style: hk.ButtonStyle = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = None,
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
    ):
        if not emoji:
            emoji = hk.Emoji.parse(emotes.NEXT.value)

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
        style: hk.ButtonStyle = hk.ButtonStyle.LINK,
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


class AddEmoteButton(nav.NavButton):
    """A custom button class for adding emotes to the server"""

    def __init__(
        self,
        *,
        style: hk.ButtonStyle = hk.ButtonStyle.PRIMARY,
        label: t.Optional[str] = "Add Emote",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
        selected_embed: t.Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )
        if selected_embed:
            self.selected_embed = selected_embed
        else:
            self.selected_embed = 0

    async def callback(self, ctx: miru.ViewContext):
        try:
            emote_name = ctx.message.embeds[self.selected_embed].title.replace(
                "Emote: ", ""
            )
            image_url = ctx.message.embeds[self.selected_embed].image.url

            emoji = await ctx.bot.rest.create_emoji(
                ctx.guild_id, name=emote_name, image=image_url
            )
            await ctx.respond(f"Added emote: {emoji.mention}")

        except Exception as e:
            await ctx.respond(f"Failed to add emote: {e}")

    async def before_page_change(self) -> None:
        ...


class PreviewButton(nav.NavButton):
    """A custom button for the manga preview"""

    def __init__(
        self,
        *,
        style: hk.ButtonStyle = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = "Preview",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
    ):
        if not emoji:
            emoji = hk.Emoji.parse("<a:peek:1061709886712455308>")
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

        for item in self.view.children:
            if not item == self:
                self.view.remove_item(item)
        data = ctx.bot.d.chapter_info[self.view.message_id]
        swap_pages = None
        if hasattr(self.view, "session"):
            swap_pages = await preview_maker(
                data[0], data[1], data[2], data[3], data[4], self.view.session
            )

        self.view.add_item(
            CustomPrevButton(
                style=hk.ButtonStyle.SECONDARY,
                emoji=hk.Emoji.parse(emotes.PREVIOUS.value),
            )
        )
        self.view.add_item(nav.IndicatorButton())
        self.view.add_item(
            CustomNextButton(
                style=hk.ButtonStyle.SECONDARY,
                emoji=hk.Emoji.parse(emotes.NEXT.value),
            )
        )

        self.view.add_item(KillNavButton())
        self.label = "🔍"
        self.emoji = None
        if swap_pages:
            await self.view.swap_pages(ctx, swap_pages)
        else:
            await ctx.respond(
                (
                    f"Looks like MangaDex doesn't have this series "
                    f"{hk.Emoji.parse(emotes.BOW)}"
                    f"\nThat or some ungabunga error."
                ),
                flags=hk.MessageFlag.EPHEMERAL,
            )
        # await ctx.edit_response(components=self.view)

    async def before_page_change(self) -> None:
        ...


class KillButton(miru.Button):
    """A custom kill button class"""

    def __init__(
        self,
        *,
        style: hk.ButtonStyle = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = "❌",
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        if self.view.message:
            await self.view.message.delete()


class NewButton(miru.Button):
    """A spitter button for the releases feed"""

    def __init__(
        self,
        style: hk.ButtonStyle = hk.ButtonStyle.SECONDARY,
        label: t.Optional[str] = None,
        link: t.Optional[str] = None,
        emoji: t.Optional[hk.Emoji] = None,
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
        style: hk.ButtonStyle = hk.ButtonStyle.SECONDARY,
        label1: t.Optional[str] = None,
        custom_id: t.Optional[str] = None,
        emoji1: t.Optional[t.Union[hk.Emoji, str]] = None,
        label2: t.Optional[str] = None,
        emoji2: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
        original_page: t.Union[hk.Embed, str],
        swap_page: t.Union[hk.Embed, str],
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
        try:
            if (self.emoji and self.emoji == self.emoji1) or (
                self.label and self.label == self.label1
            ):
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
        except Exception as e:
            await ctx.edit_response(content=e)

    async def before_page_change(self) -> None:
        ...


class SwapNaviButton(nav.NavButton):
    def __init__(
        self,
        *,
        style: hk.ButtonStyle = hk.ButtonStyle.SECONDARY,
        labels: t.Optional[t.Sequence[str]] = None,
        custom_id: t.Optional[str] = None,
        emojis: t.Optional[t.Sequence[t.Union[hk.Emoji, str]]] = None,
        row: t.Optional[int] = None,
        url: t.Optional[str] = None,
    ):
        self.labels = labels
        self.emojis = emojis

        super().__init__(
            style=style,
            label=labels[0] if labels else None,
            custom_id=custom_id,
            emoji=emojis[0] if emojis else None,
            row=row,
            url=url,
        )

    async def callback(self, ctx: miru.ViewContext):
        if self.view.message:
            if self.view.current_page == 0:
                self.view.current_page = 1

                self.label = self.labels[1] if self.labels else None
                self.emoji = self.emojis[1] if self.emojis else None

            else:
                self.view.current_page = 0
                self.label = self.labels[0] if self.labels else None
                self.emoji = self.emojis[0] if self.emojis else None

            await self.view.send_page(ctx)


class TabButton(nav.NavButton):
    def __init__(
        self,
        *,
        style: hk.ButtonStyle = hk.ButtonStyle.SECONDARY,
        active: bool = False,
        label: t.Optional[str] = None,
        custom_id: t.Optional[str] = None,
        emoji: t.Optional[t.Union[hk.Emoji, str]] = None,
        row: t.Optional[int] = None,
        url: t.Optional[str] = None,
    ):
        super().__init__(
            style=style, label=label, custom_id=custom_id, emoji=emoji, row=row, url=url
        )

    async def callback(self, ctx: miru.ViewContext):
        # self.active = True
        self.style = self.view.active_button_style
