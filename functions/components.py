"""Misc component classes"""
import typing as t

import hikari as hk
import miru

from functions.models import ALCharacter


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
            await ctx.edit_response(embeds=[self.view.pages[self.values[0]]])


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
                await ctx.edit_response(embeds=[await chara.make_embed()])

        except Exception as e:
            await ctx.respond(content=f"Error: {e}", flags=hk.MessageFlag.EPHEMERAL)
