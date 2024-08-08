"""Plugin running the background tasks and utilities for the bot"""
import asyncio
import glob
import os
import typing as t
from datetime import datetime
from random import randint
from subprocess import PIPE, Popen

import arrow
import hikari as hk
import lightbulb as lb
import pytz
from lightbulb.ext import tasks
from rapidfuzz import process
from rapidfuzz.utils import default_process

from functions.checks import trusted_user_check
from functions.models import ColorPalette as colors
from functions.models import EmoteCollection as emotes
from functions.utils import (
    check_if_url,
    humanized_list_join,
    poor_mans_proxy,
    proxy_img,
)
from functions.views import AuthorNavi

task_plugin = lb.Plugin("Tasks", "Background processes", include_datastore=True)
task_plugin.d.help = False


@tasks.task(d=2)
async def clear_session_cache():
    """Clear the bot's request session cache"""
    await task_plugin.bot.d.aio_session.delete_expired_responses()


@tasks.task(d=10)
async def clear_pic_files():
    """Clear image files"""
    print("Clearing image Files")
    files = glob.glob("./pictures/*")
    for file in files:
        os.remove(file)
    print("Cleared")


@tasks.task(d=1)
async def update_status():
    """Update the bot's status"""

    update_dict = {
        0: {
            "status": hk.Status.IDLE,
            "activity": hk.Activity(
                name="Aqua's back | -help",
                type=hk.ActivityType.WATCHING,
            ),
        },
        1: {
            "status": hk.Status.IDLE,
            "activity": hk.Activity(
                name="Bell Pepper Exercise | -help",
                type=hk.ActivityType.PLAYING,
            ),
        },
        2: {
            "status": hk.Status.IDLE,
            "activity": hk.Activity(
                name="『Idol』 | -help", type=hk.ActivityType.LISTENING
            ),
        },
    }

    chosen_status = update_dict[randint(0, 2)]

    await task_plugin.bot.update_presence(
        status=chosen_status["status"], activity=chosen_status["activity"]
    )


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("person", "The user to trust", hk.User)
@lb.command("trust", "Trust a user to access certain test commands", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def trust_user(ctx: lb.PrefixContext, person: hk.User):
    """Add a user to the trusted users' list"""
    try:
        db = ctx.bot.d.con
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO trusted_users (user_id) VALUES (?)""",
            (person.id,),
        )
        db.commit()
        await ctx.respond(f"Added user `{person.username}` to trusted users list")
    except Exception as e:
        await ctx.respond(f"Error: {e}")


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("person", "The user to remove from trusted list", hk.User)
@lb.command("untrust", "Remove a user from the list", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def distrust_user(ctx: lb.PrefixContext, person: hk.User):
    """Remove user from the trusted users' list"""
    try:
        db = ctx.bot.d.con
        cursor = db.cursor()
        cursor.execute("DELETE FROM trusted_users where user_id = ?", (person.id,))
        db.commit()
        await ctx.respond(f"Removed user `{person.username}` from trusted users list")
    except Exception as e:
        await ctx.respond(f"Error: {e}")


@task_plugin.listener(hk.GuildMessageCreateEvent)
async def custom_commands(event: hk.GuildMessageCreateEvent) -> None:
    """Listener to listen for fuzzy command matching

    Args:
        event (hk.GuildMessageCreateEvent): The event to listen for
    """

    if event.is_bot or not event.content:
        return

    app = task_plugin.bot
    prefixes = await app.get_prefix(app, event.message)

    ctx_prefix = None

    for prefix in prefixes:
        if event.content.startswith(prefix.strip()):
            ctx_prefix = prefix
            break
    else:
        return

    try:
        commandish = event.content[len(ctx_prefix) :].split()[0]

    except IndexError:  # Executed if the message is only the prefix
        # The idea being that any prefix must be under 5 characters (this will be enforced)
        prefixes_string = "\n".join(filter(lambda x: len(x) < 5 and x != "-", prefixes))

        if len(prefixes_string) == 0:
            prefixes_string = "ansi\n\u001b[0;30mNone\n"

        await app.rest.create_message(
            event.channel_id,
            embed=hk.Embed(
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
        return

    async with app.rest.trigger_typing(event.channel_id):
        prefix_commands_and_aliases = [
            command[0] for command in app.prefix_commands.items()
        ]

        if commandish in prefix_commands_and_aliases:
            pass
        else:
            close_matches: t.Optional[t.Tuple[str, int]] = process.extract(
                commandish,
                prefix_commands_and_aliases,
                score_cutoff=99,
                limit=3,
            )

            possible_commands: t.Sequence = []

            if close_matches:
                possible_commands = [i for i, *_ in close_matches]
            else:
                return

            commandish = commandish.replace(
                "@", "@\u200b"
            )  # Sanitize against ping hijacking
            await app.rest.create_message(
                event.channel_id,
                (
                    f"No command with the name `{commandish}` could be found. "
                    f"Did you mean: {humanized_list_join(possible_commands)}"
                ),
            )
            return


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("content", "The content to send", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command(
    "slideshow",
    "Create a gallery of images/text",
    aliases=["ss", "pages"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand)
async def slideshow(ctx: lb.Context, content: str) -> None:
    view = AuthorNavi(pages=content.split("\n"), user_id=ctx.author.id)
    await view.send(ctx.channel_id)


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("restart", "Update the bot's source and restart")
@lb.implements(lb.PrefixCommand)
async def update_and_restart(ctx: lb.Context) -> None:
    with Popen(["git", "pull"], stdout=PIPE, stderr=PIPE) as result:
        output, error = result.communicate(timeout=12)

        if error:
            await ctx.respond(
                f"Process returned with error: ```{(str(error, 'UTF-8'))}```"
            )
            await asyncio.sleep(3)
        else:
            await ctx.respond("Updated source.")

    await ctx.edit_last_response("Restarting the bot...")

    await ctx.bot.close()

    # try:
    #     os.kill(os.getpid(), signal.SIGTERM)
    # except Exception as e:
    #     await ctx.respond(e)


@task_plugin.command
@lb.option("image", "Image url to embed", str, required=False)
@lb.option("color", "The colour to embed", hk.Color)
@lb.command("embed", "Make embed of a color", pass_options=True, hidden=True)
@lb.implements(lb.PrefixCommand)
async def embed_color(ctx: lb.Context, color: hk.Color, image: str) -> None:
    await ctx.respond(
        embed=hk.Embed(
            color=color,
            title="Test Embed",
            description="Testing the appropriate colours for embed",
            timestamp=datetime.now().astimezone(),
        ).set_image(image)
    )


def last_n_lines(filename, num_lines):
    with Popen(["tail", f"-{num_lines}", filename], stderr=PIPE, stdout=PIPE) as pcs:
        res, err = pcs.communicate()
        if err:
            return err.decode()
    return res.decode()


@task_plugin.command
@lb.add_checks(trusted_user_check)
@lb.option("image_url", "The image to proxy")
@lb.command("proxy", "Proxy test an image", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def proxy_img_test(ctx: lb.PrefixContext, image_url: str) -> None:
    proxy = await ctx.bot.d.aio_session.get(proxy_img(image_url), timeout=2)
    await ctx.respond(
        embed=hk.Embed(title="Proxy test", description=f"Code: `{proxy.status}`")
        .set_image(await poor_mans_proxy(image_url, ctx.bot.d.aio_session))
        .set_footer(f"Requested by {ctx.author}", icon=ctx.author.avatar_url)
    )
    # except Exception as e:
    # await ctx.respond(e)


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("filename", "The log file to read", required=False)
@lb.option("num_lines", "The number of lines to fetch", int, required=False)
@lb.command(
    "latestlogs",
    "Read from the bottom and find the latest logs",
    aliases=["ll", "log"],
    pass_options=True,
    # hidden=True,
)
@lb.implements(lb.PrefixCommand)
async def latest_logs(
    ctx: lb.PrefixContext, num_lines: t.Optional[int], filename: t.Optional[str]
) -> None:
    await ctx.user.send(
        hk.Bytes(
            last_n_lines(
                f"logs/{filename}" if filename else "logs/log.txt", num_lines or 200
            ),
            "log.txt",
        )
    )
    await ctx.event.message.add_reaction("✅")
    # await ctx.respond()


# @task_plugin.command
# @lb.add_checks(lb.owner_only)
# @lb.option("link", "Link to new pfp")
# @lb.command("newpfp", "Change the bot's pfp", pass_options=True)
# @lb.implements(lb.PrefixCommand)
# async def new_bot_pfp(ctx: lb.PrefixContext, link: str):
#     try:
#         await ctx.bot.rest.edit_my_user(avatar=base64.b64encode((await poor_mans_proxy(link, ctx.bot.d.aio_session)).read()))
#         await ctx.respond("Changed bot pfp")
#     except Exception as e:
#         await ctx.respond(e)
# task_plugin.bot.rest.edit_my_user()
@task_plugin.command
@lb.add_checks(trusted_user_check)
@lb.option(
    "link",
    "The link to check",
)
@lb.command("pingu", "Check if site alive", pass_options=True, hidden=True)
@lb.implements(lb.PrefixCommand)
async def pingu(ctx: lb.Context, link: str) -> None:
    """A function to check if a site returns an OK status

    Args:
        ctx (lb.Context): The context in which the command is invoked
        link (str): The URL of the site
    """

    if not check_if_url(link):
        await ctx.respond(f"That's... not a link {emotes.POUT.value}")
        return

    try:
        if (await ctx.bot.d.aio_session.get(link, timeout=2)).ok:
            await ctx.respond(f"The site `{link}` is up and running ✅")
        else:
            await ctx.respond(
                f"The site `{link}` is either down or has blocked the client ❌"
            )
    except Exception as e:
        await ctx.respond(f"Hit an exception: `{e}`")


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("update", "Update the bot's source")
@lb.implements(lb.PrefixCommand)
async def update_code(ctx: lb.Context) -> None:
    with Popen(["git", "pull"], stdout=PIPE, stderr=PIPE) as result:
        output, error = result.communicate(timeout=12)

        if error:
            await ctx.respond(
                f"Process returned with error: ```{(str(error, 'UTF-8'))}```"
            )
            await asyncio.sleep(3)
        else:
            await ctx.respond("Updated source.")

    os.kill(os.getpgid())


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("shutdown", "shut down", aliases=["kms"])
@lb.implements(lb.PrefixCommand)
async def guilds(ctx: lb.Context) -> None:
    with open("ded.txt", "w+", encoding="UTF-8") as ded:
        ded.write(".")
    await ctx.respond("Shutting bot down...")
    await ctx.bot.close()


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("message", "The message id")
@lb.option("channel", "The channel where the message is", hk.GuildChannel)
@lb.command("del", "Delete a message", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def delete_msg(ctx: lb.Context, channel: hk.GuildChannel, message: int) -> None:
    await ctx.bot.rest.delete_message(channel=channel.id, message=message)
    await ctx.respond("Deleted", delete_after=1)
    await ctx.event.message.delete()


@task_plugin.listener(hk.StartedEvent)
async def prefix_invocation(event: hk.StartedEvent) -> None:
    await asyncio.sleep(0.5)
    conn = task_plugin.bot.d.con
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS botstats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT,
            usage INTEGER
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trusted_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER
        )
    """
    )

    conn.commit()


# @task_plugin.listener(hk.InteractionCreateEvent)
# async def global_killer(event: hk.InteractionCreateEvent) -> None:
#     if not isinstance(event.interaction, hk.ComponentInteraction):
#         return
#     print("\n\n\n")
#     # hk.ComponentInteraction.
#     print(event.interaction.component_type)
#     print(event.interaction.values)
#     print("\n\n\n")
# if isinstance():
#     ...


@task_plugin.listener(lb.CommandInvocationEvent)
async def command_invocation(event: lb.CommandInvocationEvent) -> None:
    conn = task_plugin.bot.d.con
    cursor = conn.cursor()
    command = event.command.name
    cursor.execute("SELECT usage FROM botstats WHERE command=?", (command,))
    result = cursor.fetchone()

    if result is None:
        cursor.execute(
            "INSERT INTO botstats (command, usage) VALUES (?, 1)", (command,)
        )
    else:
        count = result[0] + 1
        cursor.execute("UPDATE botstats SET usage=? WHERE command=?", (count, command))

    conn.commit()


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("stats", "Bot usage stats")
@lb.implements(lb.PrefixCommand)
async def bot_stats(ctx: lb.Context) -> None:
    conn = task_plugin.bot.d.con
    cursor = conn.cursor()
    cursor.execute("SELECT command, usage FROM botstats")
    result = cursor.fetchall()

    command, usage = ("```", "```")

    for item in result:
        command += item[0]
        command += "\n"
        usage += str(item[1])
        usage += "\n"

    command += "---\nTotal:```"
    usage += f"---\n{sum([i[1] for i in result])}```"

    await ctx.respond(
        embed=hk.Embed(title="Bot Usage Stats")
        .add_field("Command", command, inline=True)
        .add_field("Usage", usage, inline=True)
    )


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("locale", "Your locale", autocomplete=True)
@lb.option("minute", "The minute to set", autocomplete=True)
@lb.option("hour", "The hour to set timezone", autocomplete=True)
@lb.option("date", "The date to set", autocomplete=True)
@lb.option("month", "The month name to set", autocomplete=True)
@lb.option("year", "The year to set", autocomplete=True)
@lb.command(
    "timestamp",
    "Generate timezone aware timestamps for planning and stuff",
    pass_options=True,
)
@lb.implements(lb.SlashCommand)
async def timestamp_generator(
    ctx: lb.Context,
    year: str,
    month: str,
    date: str,
    hour: str,
    minute: str,
    locale: str,
) -> None:
    try:
        await ctx.respond(
            f'```<t:{int(arrow.get(f"{year.zfill(4)} {month} {date.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}", "YYYY MMMM DD HH:mm").to(locale).timestamp())}:R>```',
            flags=hk.MessageFlag.EPHEMERAL,
        )
    except Exception as e:
        await ctx.respond(e, flags=hk.MessageFlag.EPHEMERAL)


@timestamp_generator.autocomplete("year")
async def year_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    if option.value is None or option.value.strip() == "":
        curr_year = arrow.now().year
        return [str(i) for i in range(curr_year - 5, curr_year + 5)]

    years = [str(i) for i in range(1970, 2050) if str(i).startswith(option.value)]

    return years


@timestamp_generator.autocomplete("month")
async def month_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    months = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]

    if option.value is None or option.value.strip() == "":
        return [month.title() for month in months]

    close_matches = process.extract(
        option.value.lower(),
        months,
        score_cutoff=85,
        limit=None,
        processor=default_process,
    )

    months = [f"{i.title()}" for i, *_ in close_matches] if close_matches else []

    return months


@timestamp_generator.autocomplete("date")
async def date_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    if option.value is None or option.value.strip() == "":
        curr_dt = arrow.now()
        dates = [curr_dt.shift(days=i) for i in range(-5, 6)]
        return [str(date.day) for date in dates]

    return [str(i) for i in range(1, 32) if str(i).startswith(option.value)]


@timestamp_generator.autocomplete("hour")
async def hour_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    return [str(i) for i in range(0, 24) if str(i).startswith(option.value)]


@timestamp_generator.autocomplete("minute")
async def minute_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    if option.value is None or option.value.strip() == "":
        return ["00", "15", "30", "45"]

    return [str(i) for i in range(0, 60) if str(i).startswith(option.value)]


@timestamp_generator.autocomplete("locale")
async def timezone_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    tzs = list(pytz.all_timezones)
    close_matches = process.extract(
        option.value,
        tzs,
        score_cutoff=75,
        limit=24,
        processor=default_process,
    )

    locale = [f"{i}" for i, *_ in close_matches] if close_matches else []

    return locale


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(task_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(task_plugin)
