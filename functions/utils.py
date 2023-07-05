from typing import Sequence, Optional, Union
from miru.ext import nav
import hikari as hk
import datetime

class CustomNavi(nav.NavigatorView):
    def __init__(
        self, *,
        pages: Sequence[Union[str, hk.Embed, Sequence[hk.Embed]]],
        buttons: Optional[Sequence[nav.NavButton]] = None,
        timeout: Optional[Union[float, int, datetime.timedelta]] = 180.0,
        user_id: hk.Snowflake = None,
    ) -> None:
        self.user_id = user_id
        super().__init__(pages=pages, buttons=buttons, timeout=timeout)