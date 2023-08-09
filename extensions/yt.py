"""Search youtube videos"""
import os

import dotenv
import hikari as hk
import lightbulb as lb
import requests

from functions.buttons import GenericButton, KillButton
from functions.models import YTVideo

# from extensions.ping import CustomView, GenericButton, KillButton
from functions.views import CustomView

dotenv.load_dotenv()

YT_KEY = os.environ["YT_KEY"]


yt_plugin = lb.Plugin("YouTube", "Search and get songs", include_datastore=True)
yt_plugin.d.help_image = "https://i.imgur.com/dTvGa1t.png"
yt_plugin.d.help = True
yt_plugin.d.help_emoji = hk.Emoji.parse("<a:youtube:1074307805235920896>")


@yt_plugin.command
@lb.set_help(
    "**Enter a topic and get videos relating to it, pick the one you find the most suitable**"
)
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
