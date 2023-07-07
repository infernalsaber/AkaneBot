"""Get information about a role, server, user, bot etc."""
from datetime import datetime
from typing import Optional
import psutil

import hikari as hk
import lightbulb as lb
import miru


from functions.buttons import GenericButton
from functions.utils import CustomView

info_plugin = lb.Plugin("Info", "Get information about an entity")





@info_plugin.command
@lb.add_cooldown(10, 1, lb.UserBucket)
@lb.add_cooldown(15, 2, lb.ChannelBucket)
@lb.command("botinfo", "Get general info about the bot", aliases=["info"])
@lb.implements(lb.PrefixCommand)
async def botinfo(ctx: lb.Context) -> None:
    """Get info about the bot"""

    user = info_plugin.bot.get_me()
    data = await info_plugin.bot.rest.fetch_application()
    guilds = list(await info_plugin.bot.rest.fetch_my_guilds())

    member = 0
    for guild in list(info_plugin.bot.cache.get_members_view()):
        guild_obj = info_plugin.bot.cache.get_guild(guild)
        member = member + guild_obj.member_count

    view = CustomView(user_id=ctx.author.id)
    view.add_item(
        GenericButton(
            style=hk.ButtonStyle.SECONDARY,
            label="Changelog",
            emoji=hk.Emoji.parse("<:MIU_changelog:1108056158377349173>"),
        )
    )

    response = await ctx.respond(
        hk.Embed(
            color=0x43408A,
            description="A multi-purpose discord bot \
                written in hikari-py.",
        )
        .add_field("Name", user)
        .add_field("No of Servers", len(guilds), inline=True)
        .add_field("No of Members", member, inline=True)
        .add_field("Version", "v0.0.1")
        .add_field(
            "Alive since", f"<t:{int(user.created_at.timestamp())}:R>", inline=True
        )
        .add_field(
            "Up since",
            f"<t:{int(info_plugin.bot.d.timeup.timestamp())}:R>",
            inline=True,
        )
        .add_field(
            "System Usage",
            f"RAM: {psutil.virtual_memory()[2]}% (of 512MB) \nCPU: {psutil.cpu_percent(4)}%",
        )
        .set_author(name=f"{user.username} Bot")
        .set_thumbnail(user.avatar_url)
        .set_image(
            (
                "https://media.discordapp.net/attachments"
                "/1005948828484108340/1108082051246198824/69886913365.png"
            )
        )
        .set_footer(f"Made by: {data.owner}", icon=data.owner.avatar_url),
        components=view,
    )

    await view.start(response)
    await view.wait()
    if hasattr(view, "answer"):
        async with ctx.bot.d.aio_session.get(
            "https://api.github.com/repos/infernalsaber/akanebot/commits"
        ) as response:
            if response.ok:
                response = await response.json()
                changes = ""
                for i in range(4):
                    changes += f'{i+1}. `{response[i]["commit"]["committer"]["date"]}`'
                    changes += ":\u1CBC\u1CBC"
                    changes += response[i]["commit"]["message"].split("\n")[0]
                    changes += "\n"

                await ctx.respond(
                    embed=hk.Embed(description=changes, color=0x43408A).set_author(
                        name="Bot Changelog (Recent)"
                    ),
                    # reply = True,
                    flags=hk.MessageFlag.EPHEMERAL,
                )
            else:
                await ctx.respond(
                    "Failed to get changelog info.",
                    reply=True,
                    flags=hk.MessageFlag.EPHEMERAL,
                )





def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(info_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(info_plugin)
