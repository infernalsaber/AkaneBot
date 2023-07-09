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
            colour=0x000000,
            timestamp=datetime.datetime.now().astimezone()
        )
        .add_field("lookup", "Look up details on any anime, manga or character")
        .add_field("plot", "Make cool graph-y shit on the popularity of airing anime")
        .add_field("top", "Find the top anime with filters for airing, upcoming series etc.")
        .set_thumbnail(
            (
                "https://media.discordapp.net/attachments/980479966389096460"
                "/1125810202277597266/rubyhelp.png?width=663&height=662"
            )
        )
        .set_image("https://i.imgur.com/LJ1t4wD.png"),
        
        hk.Embed(
            title="Lookup Command help",
            description=(
                "Search for details of any anime, manga, novel or "
                "character."
                "\nAlias: lu"
                "\n\nNote: Please enter the full name of the series or character "
                "to avoid false matches."
                "\nEg. `-lookup anime oshi no ko` instead of `lookup anime onk`."
                "\n\n**Options** \n_anime (a)_ \n_manga (m)_ \n_novels (n)_ \n_character (c)_"
                "\n_visualnovel (vn)_"

            ),
            colour=0x000000,
            timestamp=datetime.datetime.now().astimezone()
        )
        .set_image("https://i.imgur.com/2nEsM2W.png")
        ,

        hk.Embed(
            title="Plot Command help",
            description=(
                "The command to plot the popularity of one anime during it's runtime "
                "or compare between two anime in the same season."
                "\nAlias: p"
                "\nEg."
            ),
            colour=0x000000,
            timestamp=datetime.datetime.now().astimezone()
        )
        .add_field("For a single series", "`-plot oshi no ko`")
        .add_field("To compare two series", "`-plot Jigokuraku vs Mashle`")
        .set_image("https://i.imgur.com/dTvGa1t.png")
        ,
        hk.Embed(
            title="Top Command help",
            description=(
                "Get the top 5 anime on MAL. \n"
                "Can filter the results on various parameters.\n"
                "Eg. `-top airing` would show the top 5 airing anime\n\n"
                "**Options**\n"
                "_airing_: The top rated airing anime\n"
                "_bypopularity_: The top anime by no. of members\n"
                "_upcoming_: The top upcoming anime by members\n"
                "_favorite_: THe most favourited anime\n"
                
            ),
            colour=0x000000,
            timestamp=datetime.datetime.now().astimezone()
        )
        .set_image("https://i.imgur.com/YdjzGB1.png")
        
        ,
        hk.Embed(
            title="Utility help",
            description=(
                "Misc. utility commands"
                "\n\n**ping**: Check the bot's ping"
                "\n**info**: Bot info"
            ),
            colour=0x000000,
            timestamp=datetime.datetime.now().astimezone()
        )
        .set_image("https://i.imgur.com/nsg3lZJ.png")
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
        
    sendto = None
    if isinstance(ctx, lb.SlashContext):
        sendto = ctx.interaction
    else:
        sendto = ctx.channel_id

    if not query:
        await navigator.send(sendto)
   
    elif query in ["lookup", "lu"]:
        await navigator.send(sendto, start_at=1)
        
    elif query in ["plot", "p"]:
        await navigator.send(sendto, start_at=2)
        
    elif query in ["top"]:
        await navigator.send(sendto, start_at=3)

    elif query in ["botinfo", "info", "ping"]:
        await navigator.send(sendto, start_at=4)
    
    else:
        await ctx.respond("The command you want help for probably doesn't exist")

    



def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(help_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(help_plugin)