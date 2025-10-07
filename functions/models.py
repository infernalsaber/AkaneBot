"""Utility classes for everything"""
import os
from enum import Enum, IntEnum

import dotenv
import isodate

dotenv.load_dotenv()

YT_KEY = os.getenv("YT_KEY")


class YTVideo:
    """YouTube search video class"""

    def __init__(self, search_results: dict, i: int) -> None:
        """Initializing the class"""
        self.vid_name: str = search_results["items"][i]["snippet"]["title"]
        self.vid_id: str = search_results["items"][i]["id"]["videoId"]
        self.vid_thumb: str = search_results["items"][i]["snippet"]["thumbnails"][
            "high"
        ][
            "url"
        ]  # make it medium later
        self.vid_channel: str = search_results["items"][i]["snippet"]["channelTitle"]
        self.vid_duration: str = ""

    @property
    def link(self) -> str:
        """Getting a link to the vid"""
        return f"https://www.youtube.com/watch?v={self.vid_id}"

    async def set_duration(self, req) -> str:
        """Make an API call and set the duration property"""
        ytapi2 = await req.get(
            (
                f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2Ccontent"
                f"Details%2Cstatistics&id={self.vid_id}&regionCode=US&key={YT_KEY}"
            ),
        )
        ytapi2 = await ytapi2.json()
        self.vid_duration = str(
            isodate.parse_duration(ytapi2["items"][0]["contentDetails"]["duration"])
        )
        if self.vid_duration.startswith("0:"):
            return self.vid_duration[2:]
        return self.vid_duration


class EmoteCollection(Enum):
    """Custom Emotes used by the bot"""

    SIP = "<:AkaneSip:1095068327786852453>"
    SMILE = "<:AkaneSmile:872675969041846272>"
    THINK = "<:AkaneThink:1146885037002858618>"
    POUT = "<:AkanePoutColor:852847827826376736>"
    BOW = "<a:AkaneBow:1109245003823317052>"

    PIXIV = "<:pixiv:1130216490021425352>"
    VNDB = "<:vndb_circle:1130453890307997747>"
    AL = "<:anilist:1127683041372942376>"
    NYAA = "<:nyaasi:1127717935968952440>"
    DANBOORU = "<:danbooru:1130206873388326952>"
    MANGADEX = "<:mangadex:1128015134426677318>"
    YOUTUBE = "<a:youtube:1074307805235920896>"

    NEXT = "<:pink_arrow_right:1059900771816189953>"
    PREVIOUS = "<:pink_arrow_left:1059905106075725955>"
    GEAR = "<:MIU_changelog:1108056158377349173>"
    LOADING = "<a:Loading_:1061933696648740945>"


class ColorPalette(IntEnum):
    """Commonly required colours for the bot + extras"""

    ANILIST = 0x2B2D42
    VNDB = 0x07111D  # 0x948782
    MAL = 0x2E51A2
    CAT = 0x484FC
    HELL = 0xEC2454
    SLATE_BLUE = 0x43408A
    DEFAULT = 0x43408A
    WARN = 0xFCC404
    ERROR = 0xA91B0D
    GREEN = 0x568203
    ELECTRIC_BLUE = 0x7DF9FF
    MINT = 0xBBF9F5
    PINK = 0xEF98CD
    LILAC = 0xC8A2C8
    DAWN_PINK = 0xF4EAE9
    MANGADEX = 0xFF6740
    COMICK = 0x1F2937
    IMDB = 0xF5C518
    ZZZ_DISK = 0xCBE732
    ZZZ_S_ENGINE = 0xFFB20C
    ZZZ_A_ENGINE = 0xCA46B5


ColourPalette = ColorPalette
"""Alias for :obj:`~ColorPalette`."""
