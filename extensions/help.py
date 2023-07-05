"""Make cool plot charts"""
import io
from PIL import Image

import hikari as hk
import lightbulb as lb


import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

from typing import Optional

import datetime

from functions.buttons import KillNavButton, CustomNextButton, CustomPrevButton
from functions.utils import CustomNavi

from miru.ext import nav


help_plugin = lb.Plugin(
    "Help", "Bot Help"
)



@help_plugin.command
@lb.option(
    "query",
    "The command to ask help for",
    str,
    choices = ["lookup", "plot", "info"],
    required=False
)
@lb.command(
    "help", "Plot some trends", pass_options=True,
)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def help_cmd(ctx: lb.Context, query: Optional[str] = None) -> None:
    """Compare the popularity and ratings of two different anime
    Args:
        ctx (lb.Context): The event context (irrelevant to the user)
        query (str): The name of the two anime (seperated by "vs")
    """

    pages = [
        hk.Embed(
            title="Akane Bot Help Menu",
            description="A discord bot for animanga. \n\n***Commands***",
            colour=0x43408A,
            # timestamp=datetime.datetime.now().astimezone()
        )
        .add_field("lookup", "Look up details on any anime, manga or character")
        .add_field("plot", "Make cool graph-y shit on the popularity of airing anime")
        .add_field("top", "Find the top anime with filters for airing, upcoming series etc.")
        .set_thumbnail(
            (
                "https://media.discordapp.net/attachments/980479966389096460"
                "/1125810202277597266/rubyhelp.png?width=663&height=662"
            )
        ),
        
        hk.Embed(
            title="Lookup Command help",
            description=(
                "The command to search for details of any anime, manga or "
                "character (including an easter egg for the manga lookup)."
                "\nAlias: lu"
                "\n\nNote: Please enter the full name of the series or character "
                "to avoid false matches."
                "\nEg. `-lookup anime oshi no ko` instead of `lookup anime onk`."
                "\nOptions: \nanime (a) \nmanga (m) \ncharacter (c)"
            ),
            colour=0x43408A,
            # timestamp=datetime.datetime.now().astimezone()
        )
        # .set_image("https://files.catbox.moe/72cpf3.gif")
        ,

        hk.Embed(
            title="Plot Command help",
            description=(
                "The command to plot the popularity of one anime during it's runtime"
                "or compare between two anime in the same season."
                "\nAlias: p"
                "\nEg. `-plot oshi no ko` or "
                "`plot Jigokuraku vs Mashle` to compare "
            ),
            colour=0x43408A,
            # timestamp=datetime.datetime.now().astimezone()
        )
        # .set_image("https://media.discordapp.net/attachments/1005948828484108340/1125491438801657958/image.png")
        ,
        hk.Embed(
            title="Top Command help",
            description=(
                "Get the top MAL anime. "
                "Can filter by airing, bypopularity, upcoming or favorite"
                "\nEg. `-top airing` would show the top 5 airing anime"
            ),
            colour=0x43408A,
            # timestamp=datetime.datetime.now().astimezone()
        )
        ,
        hk.Embed(
            title="Utility help",
            description=(
                "Misc. utility commands"
                "\n\n**ping**: Check the bot's ping"
                "\n**info**: Bot info"
            ),
            colour=0x43408A,
            # timestamp=datetime.datetime.now().astimezone()
        )
    ]

    buttons = [
        CustomPrevButton(), 
        nav.IndicatorButton(), 
        CustomNextButton(), 
        KillNavButton()
    ]

    navigator = CustomNavi(pages=pages, buttons=buttons, user_id=ctx.author.id)
    
    # print("Time is ", time.time()-timeInit)
    # await navigator.send(ctx.channel_id)
        
    

    if not query:
        await navigator.send(ctx.channel_id)
   
    elif query in ["lookup", "lu"]:
        await navigator.send(ctx.channel_id, start_at=1)
        
    elif query in ["plot", "p"]:
        await navigator.send(ctx.channel_id, start_at=2)
        
    elif query in ["botinfo", "info", "ping"]:
        await navigator.send(ctx.channel_id, start_at=3)
    
    else:
        await ctx.respond("The command you want help for probably doesn't exist")

    



def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(help_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(help_plugin)