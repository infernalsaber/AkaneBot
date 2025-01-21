import lightbulb as lb

from functions import buttons as btns
from functions import views as views
from functions.components import NavSelector
from functions.hakush import ZZZCharacter

anime_misc = lb.Plugin("Gacha", "Misc. stuff", include_datastore=True)
anime_misc.d.help = True
anime_misc.d.help_image = "https://i.imgur.com/YxvyvaF.png"
anime_misc.d.help_emoji = "🤔"


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
