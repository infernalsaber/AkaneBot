import lightbulb as lb

from functions import buttons as btns
from functions import views as views
from functions.components import NavSelector
from functions.hakush import ZZZCharacter
from functions.anilist_graph import format_chronological_order, find_series_name, get_anime_data
from functions.utils import get_random_quote
from curl_cffi import requests

anime_misc = lb.Plugin("Gacha", "Misc. stuff", include_datastore=True)
anime_misc.d.help = True
anime_misc.d.help_image = "https://i.imgur.com/YxvyvaF.png"
anime_misc.d.help_emoji = "🎲"

@anime_misc.command
@lb.add_cooldown(30, 3, lb.GlobalBucket)
@lb.set_max_concurrency(2, lb.GlobalBucket)
@lb.option("series", "The series to get the watch order for", modifier=lb.commands.OptionModifier.CONSUME_REST)
@lb.command("timeto", "Time investment needed by a series and watch order", aliases=['watchorder', 'wo'], pass_options=True)
@lb.implements(lb.PrefixCommand)
async def time_to(ctx: lb.Context, series: str) -> None:
    
    await ctx.respond(get_random_quote())
    with requests.Session() as session:
        anime_id = int(get_anime_data(session, anime=series)['data']['Media']['id'])
        series_list = format_chronological_order(session, anime_id=anime_id)
    order = " -> ".join(str(entry) for entry in series_list)
    total_time_investment = sum([series.episodes * series.duration for series in series_list])
    try:
        series_name = find_series_name([series.title.lower() for series in series_list]).title()
    except:
        series_name = series.title()
    
    hour, mins = divmod(total_time_investment, 60)
    time = f"{hour} hours, {mins} minutes" if mins else f"{hour} hours"
        
    await ctx.edit_last_response(
        f"The time investment required for the `{series_name}` series is {time}.\n\nThe suggested watch order, based on release date is as follows:\n{order}"
    )
    


@anime_misc.command
@lb.option("agent", "The agent to search for")
@lb.command(
    "zzz",
    "Search for a Zenless Agent",
    aliases=["zenless", "zenlesszonezero"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand)
async def zzz_chara(ctx: lb.Context, agent: str) -> None:
    chara: ZZZCharacter = await ZZZCharacter.from_search(agent, ctx.bot.d.aio_session)

    pages, options = await chara.make_pages()

    try:
        components = {}
        for page_name, page_value in pages.items():
            if len(page_value) > 1:
                components[page_name] = [
                    btns.CustomPrevButton(),
                    btns.CustomNextButton(),
                ]
            else:
                components[page_name] = []

        view = views.SelectNavigator(
            user_id=ctx.author.id,
            dropdown_options=pages,
            dropdown_components=components,
            first_page="Story",
        )
        view.add_item(NavSelector(options=options, placeholder="More Info"))
        view.add_item(btns.KillNavButton())
        await view.send(ctx.channel_id)

    except Exception as e:
        await ctx.respond(e)


def load(bot: lb.BotApp) -> None:
    # Load the plugin
    bot.add_plugin(anime_misc)


def unload(bot: lb.BotApp) -> None:
    # Unload the plugin
    bot.remove_plugin(anime_misc)
