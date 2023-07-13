"""The main file of the bot, basically sets up and starts the bot """
import asyncio
import datetime
import logging
import os

import aiohttp
import dotenv
import hikari as hk
import lightbulb as lb
import miru
from lightbulb.ext import tasks

dotenv.load_dotenv()


def return_prefix() -> list:
    if os.name == "nt":
        return [","]
    else:
        return ["-"]


# The following snippet is borrowed from:
# https://github.com/Nereg/ARKMonitorBot/blob/
# 1a6cedf34d531bddf0f5b11b3238344192998997/src/main.py#L14


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
    # set logging level to info
    root_logger.setLevel(logging.DEBUG)


bot = lb.BotApp(
    token=os.getenv("BOT_TOKEN"),
    intents=hk.Intents.ALL_UNPRIVILEGED | hk.Intents.MESSAGE_CONTENT,
    prefix=return_prefix(),
    help_class=None,
    logs="INFO",
    owner_ids=[1002964172360929343, 701090852243505212],
)

miru.install(bot)
tasks.load(bot)

bot.load_extensions_from("./extensions/")


@bot.listen()
async def on_starting(event: hk.StartingEvent) -> None:
    """Code which is executed once when the bot starts"""

    bot.d.aio_session = aiohttp.ClientSession()
    bot.d.timeup = datetime.datetime.now().astimezone()
    bot.d.chapter_info = {}
    bot.d.ncom = 0
    bot.d.update_channels = ["1127609035374461070"]
    if not os.path.exists("logs"):
        os.mkdir("logs")
        os.mkdir("pictures")
    with open("./logs/log.txt", "w+", encoding="UTF-8"):
        pass
    # with open("ded.txt", "w+", encoding="UTF-8"):
    #     pass
    setup_logging()


def verbose_timedelta(delta):
    d = delta.days
    h, s = divmod(delta.seconds, 3600)
    m, s = divmod(s, 60)
    labels = ["day", "hour", "minute", "second"]
    dhms = [
        "%s %s%s" % (i, lbl, "s" if i != 1 else "")
        for i, lbl in zip([d, h, m, s], labels)
    ]
    for start in range(len(dhms)):
        if not dhms[start].startswith("0"):
            break
    for end in range(len(dhms) - 1, -1, -1):
        if not dhms[end].startswith("0"):
            break
    return ", ".join(dhms[start : end + 1])


@bot.listen()
async def on_stopping(event: hk.StoppingEvent) -> None:
    """Code which is executed once when the bot stops"""
    # with open("ded.txt", "a", encoding="UTF-8") as ded:
    #     ded.write(".")
    await bot.rest.create_message(
        1129030476695343174,
        f"Bot closed with {bot.d.ncom} commands and {verbose_timedelta(datetime.datetime.now().astimezone()-bot.d.timeup)} uptime",
    )


@bot.command
@lb.command("ping", description="The bot's ping")
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def ping(ctx: lb.Context) -> None:
    """Check the latency of the bot

    Args:
        ctx (lb.Context): The event context (irrelevant to the user)
    """
    await ctx.respond(f"Pong! Latency: {bot.heartbeat_latency*1000:.2f}ms")
    bot.d.ncom += 1


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
        await event.context.respond("This command is only usable by bot owner")

    elif isinstance(exception, lb.CommandIsOnCooldown):
        await event.context.respond(
            f"The command is on cooldown, you can use it after {int(exception.retry_after)}s",
            delete_after=int(exception.retry_after),
        )

    elif isinstance(exception, lb.MissingRequiredPermission):
        await event.context.respond(
            "You do not have the necessary permissions to use the command",
            flags=hk.MessageFlag.EPHEMERAL,
        )

    elif isinstance(exception, lb.BotMissingRequiredPermission):
        await event.context.respond("I don't have the permissions to do this 😔")

    elif isinstance(exception, NotImplementedError):
        await event.context.respond(
            "This command has not been implemented or is not open."
        )

    elif isinstance(exception, lb.NotEnoughArguments):
        await event.context.respond(
            (
                f"Missing arguments, use `-help {event.context.command.name}`"
                f"for the correct invocation"
            )
        )


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        # pass
        import uvloop

        uvloop.install()

    bot.run(
        status=hk.Status.IDLE,
        activity=hk.Activity(name="『Idol』 | -help", type=hk.ActivityType.LISTENING),
    )
