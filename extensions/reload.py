"""Load, unload or reload a plugin"""
import lightbulb as lb


reloader_plugin = lb.Plugin("Loader", "Load, unload and reload plugins")


@reloader_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option(
    "extension",
    "The extension to reload",
    choices=["fun", "compiler", "gallery", "listener"],
)
@lb.command("reload", "Reload an extension", pass_options=True, aliases=["rl"])
@lb.implements(lb.PrefixCommand)
async def reload_plugin(ctx: lb.Context, extension: str) -> None:
    """Reload an extension"""
    ctx.bot.reload_extensions(f"extensions.{extension}")
    # try:
    #     ctx.bot.unload_extensions(f"extensions.{extension}")
    #     # await ctx.respond("oopsie. ")
    # except Exception as e:
    #     await ctx.respond(f"Couldn't unload extension: {e}")
    # else:
    #     await ctx.respond("Extension unloaded successfully.")
    #     ctx.bot.load_extensions(f"extensions.{extension}")
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


@reload_plugin.set_error_handler
async def compile_error(event: lb.CommandErrorEvent) -> bool:
    """Error handling"""
    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, lb.MissingRequiredPermission):
        await event.context.respond("You're missing some perms there, bub.")
        return True

    if isinstance(exception, lb.CommandIsOnCooldown):
        await event.context.respond(
            f"The command is on cooldown, you can use it after {int(exception.retry_after)}s",
            delete_after=int(exception.retry_after),
        )
        return True

    if isinstance(exception, lb.errors.NotEnoughArguments):
        await event.context.respond("Please specify the extension name.")
        return True

    return False


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(reloader_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(reloader_plugin)
