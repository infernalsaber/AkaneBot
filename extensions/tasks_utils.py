"""Plugin running the background tasks and utilities for the bot"""
import asyncio
import glob
import os
import subprocess
import typing as t
from datetime import datetime

import hikari as hk
import lightbulb as lb
from fuzzywuzzy import process
from lightbulb.ext import tasks

from functions.models import ColorPalette as colors
from functions.utils import check_if_url, humanized_list_join

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
        if event.content.startswith(prefix):
            ctx_prefix = prefix
            break

    if not ctx_prefix:
        return

    try:
        commandish = event.content[len(ctx_prefix) :].split()[0]

    except IndexError:  # Executed if the message is only the prefix
        # The idea being that any prefix must be under 5 characters (this will be enforced)
        prefixes_string = "\n".join(filter(lambda x: len(x) < 5, prefixes))

        await app.rest.create_message(
            event.channel_id,
            embed=hk.Embed(
                color=colors.ELECTRIC_BLUE, timestamp=datetime.now().astimezone()
            )
            .add_field("Global Prefixes", f"```{prefixes_string}```")
            .add_field("Server Prefixes", "```ansi\n\u001b[0;30mComing Soon...```")
            .add_field("Additional", "- Pinging the bot always works :)")
            .set_author(
                name="Akane Bot Prefix Configuration", icon=app.get_me().avatar_url
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
            close_matches: t.Optional[t.Tuple[str, int]] = process.extractBests(
                commandish, prefix_commands_and_aliases, score_cutoff=99, limit=3
            )

            possible_commands: t.Sequence = []

            if close_matches:
                possible_commands = [i for i, _ in close_matches]
            else:
                return

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
@lb.command("restart", "Update the bot's source and restart")
@lb.implements(lb.PrefixCommand)
async def update_and_restart(ctx: lb.Context) -> None:
    with subprocess.Popen(
        ["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as result:
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
@lb.option("color", "The colour to embed", hk.Color)
@lb.command("embed", "Make embed of a color", pass_options=True, hidden=True)
@lb.implements(lb.PrefixCommand)
async def embed_color(ctx: lb.Context, color: hk.Color) -> None:
    await ctx.respond(
        embed=hk.Embed(
            color=color,
            title="Test Embed",
            description="Testing the appropriate colours for embed",
            timestamp=datetime.now().astimezone(),
        )
    )


@task_plugin.command
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
        await ctx.respond("That's... not a link <:AkanePoutColor:852847827826376736>")
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
    with subprocess.Popen(
        ["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as result:
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

    command += "```"
    usage += "```"

    await ctx.respond(
        embed=hk.Embed(title="Bot Usage Stats")
        .add_field("Command", command, inline=True)
        .add_field("Usage", usage, inline=True)
    )


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(task_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(task_plugin)
