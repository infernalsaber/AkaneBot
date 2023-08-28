"""Load, unload or reload a plugin"""
import glob

import lightbulb as lb

reloader_plugin = lb.Plugin(
    "Loader", "Load, unload and reload plugins", include_datastore=True
)
reloader_plugin.d.help = False


@reloader_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option(
    "extension",
    "The extension to reload",
    choices=[i[13:-3].replace("/", ".") for i in glob.glob("./extensions/*.py")]
    + ["all"],
)
@lb.command("reload", "Reload an extension", pass_options=True, aliases=["rl"])
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def reload_plugin(ctx: lb.Context, extension: str) -> None:
    """Reload an extension"""

    if extension == "all":
        for i in glob.glob("./extensions/*.py"):
            i = i.replace("/", ".").replace("\\", ".")
            ctx.bot.reload_extensions(f"{i[2:-3]}")
        await ctx.respond("Reloaded all extensions")
        return

    ctx.bot.reload_extensions(f"extensions.{extension}")
    await ctx.bot.sync_application_commands()
    await ctx.respond("Extension reloaded successfully.")


@reloader_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("extension", "The extension to load")
@lb.command("load", "Load an extension", pass_options=True, aliases=["l"])
@lb.implements(lb.PrefixCommand)
async def load_plugin(ctx: lb.Context, extension: str) -> None:
    """Load an extension"""

    ctx.bot.load_extensions(f"extensions.{extension}")
    await ctx.respond(f"Extension {extension} loaded successfully.")


@reloader_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("extension", "The extension to unload")
@lb.command("unload", "Unload an extension", pass_options=True, aliases=["ul"])
@lb.implements(lb.PrefixCommand)
async def unload_plugin(ctx: lb.Context, extension: str) -> None:
    """Unload an extension"""

    ctx.bot.unload_extensions(f"extensions.{extension}")
    await ctx.respond("Extension unloaded successfully.")


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(reloader_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(reloader_plugin)
