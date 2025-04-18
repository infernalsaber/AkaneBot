"""The main file of the bot, basically sets up and starts the bot """
import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime

import aiohttp_client_cache
import hikari as hk
import lightbulb as lb
import miru
from aiohttp import ClientTimeout
from dotenv import load_dotenv
from lightbulb.ext import tasks

from functions.help import BotHelpCommand
from functions.utils import dlogger, verbose_timedelta

load_dotenv()



def make_prefix(app, message: hk.Message) -> list:
    cfg = open("config.json", encoding="utf-8")
    cfg = json.loads(cfg.read())

    guild_prefix_map = cfg["GUILD_PREFIX_MAP"]
    prefixes = guild_prefix_map.get(str(message.guild_id), ["-"])
    return prefixes


# The following snippet is borrowed from:
# https://github.com/Nereg/ARKMonitorBot/


def setup_logging() -> None:
    """Set up the logging of the events to log.txt (for debugging) [Level-1]"""

    # get root logger
    root_logger = logging.getLogger("")
    # create a rotating file handler with 1 backup file and 1 megabyte size
    file_handler = logging.handlers.RotatingFileHandler(
        "./logs/log.txt", "w+", 1_000_000, 1, "UTF-8"
    )
    # create a default console handler
    console_handler = logging.StreamHandler()
    # create a formatting style (modified from hikari)
    formatter = logging.Formatter(
        fmt="%(levelname)-1.1s %(asctime)23.23s %(name)s @ %(lineno)d: %(message)s"
    )
    # add the formatter to both handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    # add both handlers to the root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    # set logging level to debug
    root_logger.setLevel(logging.DEBUG)


bot = lb.BotApp(
    token=os.getenv("BOT_TOKEN"),
    intents=hk.Intents.ALL_UNPRIVILEGED
    # | hk.Intents.ALL_PRIVILEGED,
    | hk.Intents.MESSAGE_CONTENT | hk.Intents.GUILD_MEMBERS,
    prefix=lb.when_mentioned_or(make_prefix),
    logs="INFO",
    allow_color=False,
    owner_ids=[701090852243505212],
)

miru.install(bot)
tasks.load(bot)

bot.load_extensions_from("./extensions/")


@bot.listen()
async def on_starting(event: hk.StartingEvent) -> None:
    """Code which is executed once when the bot starts"""

    bot.d.aio_session = aiohttp_client_cache.CachedSession(
        cache_name="cache_db.db",
        expire_after=24 * 60 * 60,
        urls_expire_after={
            "*.mangadex.org": 15 * 60,
            "*.steampowered.com": 1 * 60 * 60,
        },
        allowed_codes=(200, 404),  # Cache responses with these status codes
        allowed_methods=["GET", "POST"],  # Cache requests with these HTTP methods
        include_headers=True,
        ignored_params=[
            "auth_token"
        ],  # Keep using the cached response even if this param changes
        timeout=ClientTimeout(total=10),
    )
    with open("config.json") as f:
        bot.d.config = json.load(f)
    bot.d.timeup = datetime.now().astimezone()
    bot.d.chapter_info = {}
    bot.d.con = sqlite3.connect("akane_db.db")
    os.makedirs("pictures", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    with open("./logs/log.txt", "w+", encoding="UTF-8"):
        pass

    setup_logging()


@bot.listen()
async def on_stopping(event: hk.StoppingEvent) -> None:
    """Code which is executed once when the bot stops"""

    await dlogger(
        bot,
        f"Bot closed with {verbose_timedelta(datetime.now().astimezone()-bot.d.timeup)} uptime",
    )


@bot.command
@lb.command("ping", description="The bot's ping", ephemeral=True)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def ping(ctx: lb.Context) -> None:
    """Check the latency of the bot

    Args:
        ctx (lb.Context): The event context (irrelevant to the user)
    """
    await ctx.respond(f"Pong! Latency: {bot.heartbeat_latency*1000:.2f}ms")


@bot.listen(lb.CommandErrorEvent)
async def on_error(event: lb.CommandErrorEvent) -> None:
    """The base function to listen for all errors

    Args:
        event (lb.CommandErrorEvent): The event context

    Raises:
        event.exception: Base exception probably
    """

    # Unwrap the exception to get the original cause
    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, lb.CommandInvocationError):
        await event.context.respond(
            f"Something went wrong during invocation of command `{event.context.command.name}`."
        )
        raise event.exception

    if isinstance(exception, lb.NotOwner):
        await event.context.event.message.add_reaction("❌")

    elif isinstance(exception, lb.CommandIsOnCooldown):
        await event.context.respond(
            f"The command is on cooldown, you can use it after {int(exception.retry_after)}s",
            delete_after=min(15, int(exception.retry_after)),
        )

    elif isinstance(exception, lb.MissingRequiredPermission):
        await event.context.respond(
            "You do not have the necessary permissions to use the command",
            flags=hk.MessageFlag.EPHEMERAL,
        )

    elif isinstance(exception, lb.BotMissingRequiredPermission):
        await event.context.respond("I don't have the permissions to do this 😔")

    elif isinstance(exception, lb.NotEnoughArguments):
        try:
            ctx = event.context
            command = ctx.command

            if command.hidden:
                return

            await ctx.respond("Missing arguments, initializing command help...")
            await asyncio.sleep(0.3)

            helper = BotHelpCommand(ctx.bot)

            await helper.send_command_help(ctx=ctx, command=command)

        except Exception as e:
            await event.context.respond(f"Stop, {e}")

    elif isinstance(exception, lb.OnlyInGuild):
        await event.context.respond("This command can't be invoked in DMs")

    elif isinstance(exception, lb.ConverterFailure):
        await event.context.respond(f"The argument `{exception.raw_value}` is invalid")

    elif isinstance(exception, lb.MaxConcurrencyLimitReached):
        await event.context.respond(
            "Too many people are using the command, please try again later"
        )

    elif isinstance(exception, lb.CommandNotFound):
        pass
        # To move the fuzzy matching here
    else:
        await event.context.respond("Unknown error")


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        import uvloop

        uvloop.install()

    bot.run(
        status=hk.Status.IDLE,
        activity=hk.Activity(name="『Idol』 | -help", type=hk.ActivityType.LISTENING),
    )
