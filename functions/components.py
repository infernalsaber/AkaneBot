"""Misc component classes"""
import typing as t

import miru


class HelpTextSelect(miru.TextSelect):
    def __init__(
        self,
        *,
        options: t.Sequence[miru.SelectOption],
        custom_id: str | None = None,
        placeholder: str | None = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        row: int | None = None
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
        # self.view.answer = self.values[0]
        # try:
        await ctx.edit_response(embeds=[self.view.pages[self.values[0]]])
