"""Search and/or download youtube videos"""
import os

import dotenv
import hikari as hk
import isodate
import lightbulb as lb
import miru
import requests

from extensions.ping import CustomView, GenericButton, KillButton

dotenv.load_dotenv()

YT_KEY = os.environ["yt_key"]


# TDL
# 1. Add kill butttons on -yts views ✅
# 2. Add back button on the second view of -yts
# 3. Remove view on timeout


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
        # pprint(search_results["items"][i])

    def get_link(self) -> str:
        """Getting a link to the vid"""
        return f"https://www.youtube.com/watch?v={self.vid_id}"

    def set_duration(self, req) -> str:
        """Make an API call and set the duration property"""
        ytapi2 = req.get(
            (
                f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2Ccontent"
                f"Details%2Cstatistics&id={self.vid_id}&regionCode=US&key={YT_KEY}"
            )
        )
        ytapi2 = ytapi2.json()
        self.vid_duration = str(
            isodate.parse_duration(ytapi2["items"][0]["contentDetails"]["duration"])
        )
        if self.vid_duration.startswith("0:"):
            self.vid_duration = str(
                isodate.parse_duration(ytapi2["items"][0]["contentDetails"]["duration"])
            )[2:]
            return self.vid_duration[2:]
        return self.vid_duration

    def get_duration_secs(self) -> int:
        """Get the duration in seconds"""
        ytapi2 = requests.get(
            (
                f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2Ccontent"
                f"Details%2Cstatistics&id={self.vid_id}&regionCode=US&key={YT_KEY}"
            ),
            timeout=10,
        )
        ytapi2 = ytapi2.json()
        return int(
            isodate.parse_duration(
                (ytapi2["items"][0]["contentDetails"]["duration"])
            ).total_seconds()
        )


# class boolButton(miru.View):
#     @miru.button(label="✅", style=hk.ButtonStyle.SUCCESS)
#     async def first(self, button: miru.Button, ctx: miru.ViewContext) -> None:
#         await ctx.respond("You clicked me!", flags=hk.MessageFlag.EPHEMERAL)

#     @miru.button(label="❌", style=hk.ButtonStyle.SECONDARY)
#     async def first(self, button: miru.Button, ctx: miru.ViewContext) -> None:
#         await ctx.respond("You clicked me!", flags=hk.MessageFlag.EPHEMERAL)


class YesButton(miru.Button):
    """Make a Yes Button class"""

    def __init__(self) -> None:
        # Initialize our button with some pre-defined properties
        super().__init__(style=hk.ButtonStyle.SUCCESS, label="Yes")

    # The callback is the function that gets called when the button is pressed
    # If you are subclassing, you must use the name "callback" when defining it.
    async def callback(self, ctx: miru.ViewContext) -> None:
        # You can specify the ephemeral message flag to make your response ephemeral
        # await ctx.respond("I'm sorry but this is unacceptable.", flags=hk.MessageFlag.EPHEMERAL)
        # You can access the view an item is attached to by accessing it's view property
        self.view.answer = True
        self.view.stop()


class NoButton(miru.Button):
    """Make a no button class"""

    # Let's leave our arguments dynamic this time, instead of hard-coding them
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.ViewContext) -> None:
        # await ctx.respond("This is the only correct answer.", flags=hk.MessageFlag.EPHEMERAL)
        self.view.answer = False
        self.view.stop()


# class choiceButtons(miru.View):
#     # def __init__(self) -> None:
#     #     super.__init__(timeout=None)

#     @miru.button(label="1", style=hk.ButtonStyle.SECONDARY)
#     async def callback(self, button: miru.Button, ctx: miru.ViewContext) -> None:
#         await ctx.respond("You clicked me!", flags=hk.MessageFlag.EPHEMERAL)

#     @miru.button(label="new button", style=hk.ButtonStyle.SUCCESS)
#     async def second(self, button: miru.Button, ctx: miru.ViewContext) -> None:
#         await ctx.respond("You clicked neeww")


yt_plugin = lb.Plugin("YouTube", "Search and get songs")


@yt_plugin.command
@lb.option(
    "query", "The topic to search for", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command(
    "youtubesearch", "Search YouTube and get videos", aliases=["yt"], pass_options=True
)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def youtube_search(ctx: lb.Context, query: str) -> None:
    """Search youtube for a video query

    Args:
        ctx (lb.Context): The event context (irrelevant to the user)
        query (str): The query to search for
    """

    if not (guild := ctx.get_guild()):
        await ctx.respond("This command may only be used in servers.")
        return
    try:
        req = requests.Session()
        response_params = {
            "part": "snippet",
            "maxResults": "6",
            "q": query,
            "regionCode": "US",
            "key": YT_KEY,
        }

        response = req.get(
            " https://youtube.googleapis.com/youtube/v3/search", params=response_params
        )
        # print(type(response.json()))
        if not response.ok:
            await ctx.respond(f"Error occurred 😵, code `{response.status_code}`")
            return

        embed = hk.Embed()
        lst_vids = []
        embed.set_footer(f"Requested by: {ctx.author}", icon=ctx.author.avatar_url)
        view = CustomView(user_id=ctx.author.id)
        for i in range(5):
            qvideo = YTVideo(response.json(), i)
            qvideo.set_duration(req)
            embed.add_field(
                f"`{i+1}.`",
                (
                    f"```ansi\n\u001b[0;35m{qvideo.vid_name} \u001b[0;36m"
                    f"[{qvideo.vid_duration[2:] if qvideo.vid_duration.startswith('0:') else qvideo.vid_duration}] ```"
                ),
            )
            lst_vids.append(qvideo)

            view.add_item(GenericButton(style=hk.ButtonStyle.SECONDARY, label=f"{i+1}"))
        view.add_item(KillButton(style=hk.ButtonStyle.DANGER, label="❌"))

        # view.add_item(NoButton(style=hk.ButtonStyle.DANGER, label="No"))
        choice = await ctx.respond(embed=embed, components=view)
        # vid_index = choice - 1
        await view.start(choice)
        await view.wait()
        # view.from_message(message)
        if hasattr(view, "answer"):  # Check if there is an answer
            await ctx.edit_last_response(
                f"Video link: {lst_vids[int(view.answer)-1].get_link()}",
                embeds=[],
                # flags=hk.MessageFlag.SUPPRESS_EMBEDS,
                components=[],
            )
        else:
            await ctx.edit_last_response("Process timed out.", embeds=[], views=[])
            return
    except Exception as e:
        print(e)


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(yt_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(yt_plugin)
