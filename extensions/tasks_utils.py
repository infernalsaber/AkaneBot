"""Plugin running the background tasks and utilities for the bot"""
import asyncio
import datetime
import glob
import os
import subprocess

import hikari as hk
import lightbulb as lb
from lightbulb.ext import tasks

from extensions.ping import CustomNavi
from extensions.ping import CustomNextButton
from extensions.ping import CustomPrevButton
from extensions.ping import KillNavButton

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
    ctx.bot.d.ncom += 1

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
@lb.command("update", "Update the bot's source", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def update_code(ctx: lb.Context) -> None:
    ctx.bot.d.ncom += 1

    with subprocess.Popen(
        ["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as result:
        output, error = result.communicate(timeout=12)
        print(output, error)
        if error:
            await ctx.respond(
                f"Process returned with error: ```{(str(error, 'UTF-8'))}```"
            )
            asyncio.sleep(3)
        else:
            await ctx.respond("Updated source.")

    await ctx.edit_last_response("Restarting the bot...")
    check = "ps aux | grep bot.py | grep -v 'grep' | awk '{print $2}'"
    process = subprocess.Popen(
            check, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    stdout, stderr = process.communicate()
    os.system(f'kill {int.from_bytes(stdout, byteorder="big")}')

@task_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("guilds", "Update the bot's source")
@lb.implements(lb.PrefixCommand)
async def guilds(ctx: lb.Context) -> None:
    ctx.bot.d.ncom += 1

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
    ctx.bot.d.ncom += 1
    with open("ded.txt", "w+", encoding="UTF-8") as ded:
        ded.write(".")
    await ctx.respond("Shutting bot down...")
    await ctx.bot.close()


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(task_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(task_plugin)
