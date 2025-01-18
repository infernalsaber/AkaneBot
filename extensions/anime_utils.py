import hikari as hk
import lightbulb as lb
from functions.hakush import ZZZCharacter
from functions import views as views
from functions import buttons as btns
from functions.components import SimpleTextSelect

anime_misc = lb.Plugin('Misc', 'Misc. stuff')


    
@anime_misc.command
@lb.option(
    'agent',
    'The agent to search for'
)
@lb.command('zzz', 'Search for a Zenless Agent', pass_options=True)
@lb.implements(lb.PrefixCommand)
async def zzz_chara(ctx: lb.Context, agent: str) -> None:
    chara: ZZZCharacter = await ZZZCharacter.from_search(agent, ctx.bot.d.aio_session)
    
    pages, options = await chara.make_pages()
    first_page = pages['Story']
    
    
    view = views.SelectView(user_id=ctx.author.id, pages=pages)
    view.add_item(SimpleTextSelect(options=options, placeholder="More Fun Stuff"))
    view.add_item(btns.KillButton())

    resp = await ctx.respond(content=None, embed=first_page, components=view)
    await view.start(resp)
    await view.wait()
    

def load(bot: lb.BotApp) -> None:
# Load the plugin
    bot.add_plugin(anime_misc)


def unload(bot: lb.BotApp) -> None:
# Unload the plugin
    bot.remove_plugin(anime_misc)