"""Plugin running the background tasks and utilities for the bot"""
import asyncio
import datetime
import glob
import os
import subprocess

import hikari as hk
import lightbulb as lb
from lightbulb.ext import tasks

from extensions.ping import (
    CustomNavi,
    CustomNextButton,
    CustomPrevButton,
    KillNavButton,
)

task_plugin = lb.Plugin("Tasks", "Background processes")


@tasks.task(d=1)
async def remove_lookup_data():
    task_plugin.bot.d.chapter_info = {}


@tasks.task(d=10)
async def clear_pic_files():
    """Clear image files"""
    print("Clearing image Files")
    files = glob.glob("./pictures/*")
    for file in files:
        os.remove(file)
    print("Cleared")


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("dir", "Upload media files from the cwd", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def directory(ctx: lb.Context) -> None:
    """Get media files from the directory, this to be used is if a command fails

    Args:
        ctx (lb.Context): The event context (irrelevant to the user)
    """

    if not (guild := ctx.get_guild()):
        await ctx.respond("This command may only be used in servers.")
        return

    embed = hk.Embed()
    view = miru.View()

    if len(os.listdir("./pictures")) > 20:
        await ctx.respond("Too many items. Can't list")
        return

    for i, item in enumerate(["./pictures"]):
        embed.add_field(f"`{i+1}.`", f"```ansi\n\u001b[0;35m{item} ```")
        view.add_item(GenericButton(style=hk.ButtonStyle.SECONDARY, label=str(item)))
    view.add_item(KillButton(style=hk.ButtonStyle.DANGER, label="❌"))

    choice = await ctx.respond(embed=embed, components=view)

    await view.start(choice)
    await view.wait()

    if not hasattr(view, "answer"):
        await ctx.edit_last_response("Process timed out", embeds=[], components=[])
        return

    folder = view.answer

    embed2 = hk.Embed()
    view2 = miru.View()

    for i, item in enumerate(os.listdir(f"./{folder}")):
        embed2.add_field(f"`{i+1}.`", f"```ansi\n\u001b[0;35m{item} ```")

        view2.add_item(GenericButton(style=hk.ButtonStyle.SECONDARY, label=f"{i+1}"))
    view2.add_item(KillButton(style=hk.ButtonStyle.DANGER, label="❌"))
    # view.

    choice = await ctx.edit_last_response(embed=embed2, components=view2)

    await view2.start(choice)
    await view2.wait()

    if hasattr(view2, "answer"):  # Check if there is an answer
        await ctx.edit_last_response(content="Here it is.", embeds=[], components=[])
        filez = os.listdir(f"./{folder}")[int(view2.answer) - 1]
    else:
        await ctx.edit_last_response("Process timed out.", embeds=[], components=[])
        return

    await ctx.respond(attachment=f"{folder}/{filez}")


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("restart", "Update the bot's source and restart", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def update_code(ctx: lb.Context) -> None:
    with subprocess.Popen(
        ["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as result:
        output, error = result.communicate(timeout=12)
        print(output, error)
        if error:
            await ctx.respond(
                f"Process returned with error: ```{(str(error, 'UTF-8'))}```"
            )
            await asyncio.sleep(3)
        else:
            await ctx.respond("Updated source.")

    await ctx.edit_last_response("Restarting the bot...")

    os.kill(os.getpgid())


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("update", "Update the bot's source", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def update_code(ctx: lb.Context) -> None:
    with subprocess.Popen(
        ["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as result:
        output, error = result.communicate(timeout=12)
        print(output, error)
        if error:
            await ctx.respond(
                f"Process returned with error: ```{(str(error, 'UTF-8'))}```"
            )
            await asyncio.sleep(3)
        else:
            await ctx.respond("Updated source.")


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("guilds", "Update the bot's source")
@lb.implements(lb.PrefixCommand)
async def guilds(ctx: lb.Context) -> None:
    pages = []
    buttons = [CustomPrevButton(), KillNavButton(), CustomNextButton()]
    for gld in list([guild for guild in ctx.bot.cache.get_guilds_view().values()]):
        pages.append(
            hk.Embed(
                color=0xF4EAE9,
                title=f"Server: {gld.name}",
                description=f"Server ID: `{gld.id}`",
                timestamp=datetime.datetime.now().astimezone(),
            )
            .add_field("Owner", await gld.fetch_owner(), inline=True)
            .add_field(
                "Server Created",
                f"<t:{int(gld.created_at.timestamp())}:R>",
                inline=True,
            )
            .add_field("Member Count", gld.member_count)
            .add_field("Boosts", gld.premium_subscription_count or "NA", inline=True)
            .add_field("Boost Level", gld.premium_tier or "NA", inline=True)
            .set_thumbnail(gld.icon_url)
            .set_image(gld.banner_url)
        )

    navigator = CustomNavi(pages=pages, buttons=buttons, user_id=ctx.author.id)
    await navigator.send(ctx.channel_id)


@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("shutdown", "shut down")
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
@lb.command("del", "Unload an extension", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def delete_msg(ctx: lb.Context, channel: hk.GuildChannel, message: int) -> None:
    await ctx.bot.rest.delete_message(channel=channel.id, message=message)
    await ctx.respond("Deleted", delete_after=1)
    await ctx.event.message.delete()

@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.option("sticker", "The channel where the message is", hk.GuildSticker)
@lb.command("stinfo", "Unload an extension", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def sticker_info(ctx: lb.Context, sticker: hk.GuildSticker) -> None:
    await ctx.respond(
        embed=hk.Embed(
            color=0x00FFFF
        )
        .add_field("Tag", sticker.tag)
        .add_field("Type", sticker.type)
        .add_field("Description", sticker.description)
        .add_field("Name", sticker.name)
        .add_field("Format Type", sticker.format_type)
        .set_image(sticker.image_url)
    )
    # ctx.bot.rest.sched

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


@task_plugin.listener(lb.CommandInvocationEvent)
async def prefix_invocation(event: lb.CommandInvocationEvent) -> None:
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
@lb.command("stats", "Unload an extension")
@lb.implements(lb.PrefixCommand)
async def bot_stats(ctx: lb.Context) -> None:
    try:
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

    except Exception as e:
        print(e)

    # if result is None:

    #     cursor.execute("INSERT INTO botstats (command, usage) VALUES (?, 1)", (command,))

    # conn.commit()


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(task_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(task_plugin)
