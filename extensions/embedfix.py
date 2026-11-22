"""Replies to links from sites with broken Discord embeds with a proper embed"""

import json
import logging

import hikari as hk
import lightbulb as lb

from utils import embedfix

logger = logging.getLogger(__name__)

embedfix_plugin = lb.Plugin(
    "EmbedFix", "Fixes embeds of supported links", include_datastore=True
)
embedfix_plugin.d.help = False


@embedfix_plugin.listener(hk.GuildMessageCreateEvent)
async def fix_embeds(event: hk.GuildMessageCreateEvent) -> None:
    """Reply with a proper embed for the first supported link in a message"""
    bot = embedfix_plugin.bot
    if event.is_bot or not event.content or not bot.d.config.get("EMBEDFIX_ENABLED"):
        return

    for pattern, handler in embedfix.HANDLERS:
        match = pattern.search(event.content)
        if not match:
            continue

        try:
            embed = await handler(match, bot.d.aio_session)
        except Exception:
            logger.warning(f"Embed fix failed for {match.group(0)}", exc_info=True)
            return

        if not embed:
            return

        await event.message.respond(embed=embed, reply=True, mentions_reply=False)
        try:
            await event.message.edit(flags=hk.MessageFlag.SUPPRESS_EMBEDS)
        except hk.HTTPError:
            pass  # Hiding the original preview needs Manage Messages
        return


@embedfix_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("state", "on or off")
@lb.command("embedfix", "Turn embed fixing on or off everywhere", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def toggle_embedfix(ctx: lb.PrefixContext, state: str) -> None:
    """Flip the global embed fixing flag and save it to config.json"""
    state = state.lower()
    if state not in ("on", "off"):
        return await ctx.respond("Usage: `-embedfix on` or `-embedfix off`")

    with open("config.json", encoding="utf-8") as file:
        config = json.load(file)

    config["EMBEDFIX_ENABLED"] = state == "on"
    with open("config.json", "w", encoding="utf-8") as file:
        file.write(json.dumps(config, indent=4))

    ctx.bot.d.config["EMBEDFIX_ENABLED"] = config["EMBEDFIX_ENABLED"]
    await ctx.respond(f"Embed fixing is now **{state}** everywhere.")


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(embedfix_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(embedfix_plugin)
