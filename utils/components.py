"""Misc component classes"""
import typing as t

import hikari as hk
import miru
from miru.ext import nav

import utils.buttons as btns
from utils.anilist import ALCharacter


class SimpleTextSelect(miru.TextSelect):
    """A simple text select which switches between a pages dictionary based on user choice"""

    def __init__(
        self,
        *,
        options: t.Sequence[miru.SelectOption],
        custom_id: str | None = None,
        placeholder: str | None = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        row: int | None = None,
    ) -> None:
        super().__init__(
            options=options,
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
            row=row,
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        if hasattr(self.view, "pages"):
            val = self.view.pages[self.values[0]]
            embeds_list = val if isinstance(val, list) else [val]
            await ctx.edit_response(embeds=embeds_list)


class SwapTextSelect(miru.TextSelect):
    """A text select that updates embeds and an associated SwapButton's target content."""

    def __init__(
        self,
        *,
        options: t.Sequence[miru.SelectOption],
        swap_attr: str = "trailers",
        custom_id: str | None = None,
        placeholder: str | None = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        row: int | None = None,
    ) -> None:
        super().__init__(
            options=options,
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
            row=row,
        )
        self.swap_attr = swap_attr

    async def callback(self, ctx: miru.ViewContext) -> None:
        selected_id = self.values[0]
        if hasattr(self.view, "pages") and selected_id in self.view.pages:
            new_embed = self.view.pages[selected_id]
            swap_data = getattr(self.view, self.swap_attr, {}).get(selected_id)

            for child in self.view.children:
                if isinstance(child, btns.SwapButton):
                    child.original_page = new_embed
                    child.swap_page = swap_data
                    child.label = child.label1
                    child.emoji = child.emoji1
                    break

            embeds_list = new_embed if isinstance(new_embed, list) else [new_embed]
            await ctx.edit_response(content=None, embeds=embeds_list, components=self.view)



class CharacterSelect(miru.TextSelect):
    """A text select made for the character command's dropdown"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.ViewContext) -> None:
        try:
            if hasattr(self.view, "session"):
                chara = await ALCharacter.from_id(
                    int(self.values[0]), self.view.session
                )
                if chara is None:
                    await ctx.respond(
                        content="Character lookup failed", flags=hk.MessageFlag.EPHEMERAL
                    )
                    return
                await ctx.edit_response(embeds=[await chara.make_embed()], content=None)

        except Exception as e:
            await ctx.respond(content=f"Error: {e}", flags=hk.MessageFlag.EPHEMERAL)


class NavSelector(nav.NavTextSelect):
    def __init__(
        self,
        *,
        options: t.Sequence[miru.SelectOption],
        custom_id: str | None = None,
        placeholder: str | None = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        row: int | None = None,
    ) -> None:
        super().__init__(
            options=options,
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
            row=row,
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        if hasattr(self.view, "dropdown_options") and hasattr(
            self.view, "dropdown_components"
        ):
            base_components = [self, btns.KillNavButton()]
            new_components = (
                self.view.dropdown_components.get(self.values[0], []) + base_components
            )
            try:
                view = self.view

                self.view.clear_items()

                for component in new_components:
                    if component not in view.children:
                        view.add_item(component)
                await view.swap_pages(ctx, view.dropdown_options[self.values[0]])
            except Exception as e:
                pass
