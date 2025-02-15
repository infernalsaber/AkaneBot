import json
import sys
import typing as t
from datetime import datetime

import hikari as hk
import lightbulb as lb

from functions.models import ColorPalette as colors
from functions.utils import humanized_list_join

prefix_manager = lb.Plugin("Prefix", "manager", include_datastore=True)
prefix_manager.d.help = True


def validate_guild_prefix(pfx: str) -> bool:
    """Ensure a valid guild prefix
    The validation conditions being:
    i. The prefix is less than 5 characters
    ii. The prefix is not empty/space
    iii. The prefix does not contain a double quote
    """
    return len(pfx) < 5 and len(pfx.strip()) > 0 and '"' not in pfx


@prefix_manager.command
@lb.command("prefix", "Prefix manager wizard", aliases=["pfx"])
@lb.implements(lb.PrefixCommandGroup)
async def prefix_group(ctx: lb.PrefixContext) -> None:
    if len(ctx.event.message.content.strip().split()) == 1:
        try:
            app = ctx.bot
            prefixes_string = "\n".join(
                filter(
                    lambda x: len(x) < 5 and x != "-",
                    await app.get_prefix(app, ctx.event.message),
                )
            )

            if len(prefixes_string) == 0:
                prefixes_string = "ansi\n\u001b[0;30mNone\n"

            await ctx.respond(
                hk.Embed(
                    color=colors.ELECTRIC_BLUE, timestamp=datetime.now().astimezone()
                )
                .add_field("Global Prefixes", "```-```")
                .add_field("Server Prefixes", f"```{prefixes_string}```")
                .add_field("Additional", "- Pinging the bot always works :)")
                .set_author(
                    name=f"{app.get_me().username} Prefix Configuration",
                    icon=app.get_me().avatar_url,
                ),
            )
        except Exception:
            await ctx.respond(sys.exc_info())
    else:
        pass


@prefix_group.child
@lb.add_checks(lb.owner_only | lb.has_guild_permissions(hk.Permissions.ADMINISTRATOR))
@lb.option(
    "prefixes",
    "The prefix to add (guild specific)",
    modifier=lb.OptionModifier.GREEDY,
)
@lb.command("add", "Add prefix(es)", aliases=["a"], pass_options=True)
@lb.implements(lb.PrefixSubCommand)
async def add_prefix(ctx: lb.Context, prefixes: t.Sequence[str]) -> None:
    try:
        file_mngr = open("config.json", encoding="utf-8")

        config = json.loads(file_mngr.read())

        curr_guild_pfxs = config["GUILD_PREFIX_MAP"].get(str(ctx.guild_id))

        if curr_guild_pfxs is None:
            curr_guild_pfxs = ["-"]

        if len(prefixes + curr_guild_pfxs) > 3:
            await ctx.respond("A server can only have upto 3 prefixes")
            return

        for pfx in prefixes:
            if not validate_guild_prefix(pfx):
                await ctx.respond(f"Can't add invalid prefix: `{pfx}`")
                prefixes.remove(pfx)

        curr_guild_pfxs += prefixes

        config["GUILD_PREFIX_MAP"][str(ctx.guild_id)] = list(set(curr_guild_pfxs))

        ctx.bot.d.config = config

        file_mngr = open("config.json", "w", encoding="utf-8")
        file_mngr.write(json.dumps(config, indent=4))

    except Exception:
        await ctx.respond(sys.exec_info())

    prefixes = [f"`{pfx}`" for pfx in prefixes]
    curr_guild_pfxs = [f"`{pfx}`" for pfx in curr_guild_pfxs]

    await ctx.respond(
        f"Added prefixes: {humanized_list_join(prefixes, conj='and')}\n"
        f"All valid prefixes are: {humanized_list_join(curr_guild_pfxs, conj='and')}"
    )


@prefix_group.child
@lb.add_checks(lb.owner_only | lb.has_guild_permissions(hk.Permissions.ADMINISTRATOR))
@lb.option("prefix_", "The prefix to set")
@lb.command(
    "set",
    "Set a prefix, overriding the global prefix",
    aliases=["s"],
    pass_options=True,
)
@lb.implements(lb.PrefixSubCommand)
async def set_prefix(ctx: lb.Context, prefix_: str) -> None:
    if not validate_guild_prefix(prefix_):
        return await ctx.respond(f"Can't set invalid prefix: `{prefix_}`")

    f = open("config.json", encoding="utf-8")
    config = json.loads(f.read())
    f.close()

    curr_guild_pfxs = config["GUILD_PREFIX_MAP"].get(str(ctx.guild_id))
    curr_guild_pfxs = [prefix_]

    config["GUILD_PREFIX_MAP"][str(ctx.guild_id)] = curr_guild_pfxs

    ctx.bot.d.config = config

    f = open("config.json", "w", encoding="utf-8")
    f.write(json.dumps(config, indent=4))
    f.close()

    await ctx.respond(f"Your set server prefix is: `{prefix_}`")


@prefix_group.child
@lb.add_checks(lb.owner_only | lb.has_guild_permissions(hk.Permissions.ADMINISTRATOR))
@lb.command(
    "reset", "Reset guild prefixes, revert back to global ones", aliases=["rst"]
)
@lb.implements(lb.PrefixSubCommand)
async def reset_prefix(ctx: lb.Context) -> None:
    f = open("config.json", encoding="utf-8")
    config = json.loads(f.read())
    f.close()

    config["GUILD_PREFIX_MAP"].remove([str(ctx.guild_id)])

    ctx.bot.d.config = config

    f = open("config.json", "w", encoding="utf-8")
    f.write(json.dumps(config, indent=4))
    f.close()

    await ctx.respond("Reset guild specific prefixes")


@prefix_group.child
@lb.add_checks(lb.owner_only | lb.has_guild_permissions(hk.Permissions.ADMINISTRATOR))
@lb.option("prefix_", "The prefix to remove")
@lb.command("remove", "Remove a guild prefix", aliases=["rm", "r"], pass_options=True)
@lb.implements(lb.PrefixSubCommand)
async def remove_prefix(ctx: lb.Context, prefix_: str) -> None:
    f = open("config.json", encoding="utf-8")
    config = json.loads(f.read())
    f.close()

    curr_guild_pfxs = config["GUILD_PREFIX_MAP"][str(ctx.guild_id)]
    if prefix_ not in curr_guild_pfxs:
        await ctx.respond(f"Prefix `{prefix_}` not found")
        return

    curr_guild_pfxs.remove(prefix_)
    config["GUILD_PREFIX_MAP"][str(ctx.guild_id)] = curr_guild_pfxs

    ctx.bot.d.config = config

    f = open("config.json", "w", encoding="utf-8")
    f.write(json.dumps(config, indent=4))
    f.close()

    await ctx.respond(f"Removed the prefix: `{prefix_}`")
    curr_guild_pfxs = [f"`{pfx}`" for pfx in curr_guild_pfxs]
    await ctx.edit_last_response(
        f"Removed the prefix: `{prefix_}`"
        f"\nCurrent prefixes: {humanized_list_join(curr_guild_pfxs, conj='and')}"
    )


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(prefix_manager)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(prefix_manager)
