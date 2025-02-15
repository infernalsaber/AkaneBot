"""Search youtube videos"""
import os

import dotenv
import hikari as hk
import lightbulb as lb

from functions.buttons import GenericButton, KillButton
from functions.models import EmoteCollection as emotes
from functions.models import YTVideo
from functions.views import AuthorView

dotenv.load_dotenv()

YT_KEY = os.getenv("YT_KEY")


yt_plugin = lb.Plugin("YouTube", "Search and get songs", include_datastore=True)
yt_plugin.d.help_image = "https://i.imgur.com/dTvGa1t.png"
yt_plugin.d.help = True
yt_plugin.d.help_emoji = hk.Emoji.parse(emotes.YOUTUBE.value)


def fuck_pep8(duration: str) -> str:
    """Coz yeah"""
    return duration[2:] if duration.startswith("0:") else duration


@yt_plugin.command
@lb.add_checks(lb.guild_only)
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

    response_params = {
        "part": "snippet",
        "maxResults": "6",
        "q": query,
        "regionCode": "US",
        "key": YT_KEY,
    }

    response = await ctx.bot.d.aio_session.get(
        "https://youtube.googleapis.com/youtube/v3/search",
        params=response_params,
    )

    if not response.ok:
        await ctx.respond(f"Error occurred 😵, code `{response.status_code}`")
        return

    embed = hk.Embed()
    lst_vids = []
    embed.set_footer(f"Requested by: {ctx.author}", icon=ctx.author.avatar_url)
    view = AuthorView(user_id=ctx.author.id)
    for i in range(5):
        qvideo = YTVideo(await response.json(), i)
        await qvideo.set_duration(ctx.bot.d.aio_session)
        embed.add_field(
            f"`{i+1}.`",
            (
                f"```ansi\n\u001b[0;35m{qvideo.vid_name} \u001b[0;36m"
                f"[{fuck_pep8(qvideo.vid_duration)}] ```"
            ),
        )
        lst_vids.append(qvideo)

        view.add_item(GenericButton(style=hk.ButtonStyle.SECONDARY, label=f"{i+1}"))
    view.add_item(KillButton(style=hk.ButtonStyle.DANGER, label="❌"))

    choice = await ctx.respond(embed=embed, components=view)
    await view.start(choice)
    await view.wait()

    if hasattr(view, "answer"):  # Check if there is an answer
        await ctx.edit_last_response(
            f"Video link: {lst_vids[int(view.answer)-1].link}",
            embeds=[],
            components=[],
        )
    else:
        # Checking if message isn't deleted by now
        if ctx.responses:
            await ctx.edit_last_response("Process timed out.", embeds=[], components=[])
        return


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(yt_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(yt_plugin)
