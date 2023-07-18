"""To send manga updates (IN PRODUCTION)"""
import sqlite3

import hikari as hk
import lightbulb as lb
import requests
from tabulate import tabulate

updates = lb.Plugin("Manga Updates", "muh mangasee")


@updates.listener(hk.StartingEvent)
async def on_starting(event: hk.StartingEvent) -> None:
    """Event fired on start of bot"""
    # return
    conn = sqlite3.connect("akane_db.db")
    cursor = conn.cursor()
    updates.bot.d.con = conn

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS manga (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manga_name TEXT,
        manga_link TEXT,
        guild_id INTEGER,
        guild_channel INTEGER,
        latest_chapter INTEGER,
        custom_text TEXT
    )
"""
    )

    # while True:
    #     updates.bot.rest.create_message()

    # updates.bot.rest.create_message()


@updates.listener(hk.StoppingEvent)
async def on_stopping(event: hk.StoppingEvent) -> None:
    """Event fired on stopping the bot"""
    updates.bot.d.db.close()


@updates.command
@lb.add_checks()
@lb.option("id", "ID of the series to unsub")
@lb.command(
    "unsubscribe", "Don't send manga updates", pass_options=True, aliases=["unsub"]
)
@lb.implements(lb.PrefixCommand)
async def subs(ctx: lb.Context, id: int) -> None:
    """Send the log file folder as a .rar file"""

    await ctx.respond("ok")
    try:
        if not ctx.get_guild().id in [980479965726404670]:
            await ctx.respond("no")
            return
        db = ctx.bot.d.con
        cursor = db.cursor()
        cursor.execute("DELETE FROM manga where id = ?", id)
        db.commit()
        # rows = cursor.fetchall()
        # print(rows)
        # rows.insert(0, ("Name", "Channel", "Last Chapter"))

        # # output = [("Name", "Channel", "Last Chapter")]
        # output = tabulate(rows, headers='firstrow')
        # # output.insert(0, ("Name", "Channel", "Last Chapter"))
        await ctx.respond("Unsubscribed")
    except Exception as e:
        print(e)


@updates.command
@lb.add_checks()
@lb.command(
    "subscriptions",
    "Send server manga subscriptions",
    pass_options=True,
    aliases=["subs"],
)
@lb.implements(lb.PrefixCommand)
async def subs(ctx: lb.Context) -> None:
    """Send the log file folder as a .rar file"""

    await ctx.respond("ok")
    try:
        if not ctx.get_guild().id in [980479965726404670]:
            await ctx.respond("no")
            return
        db = ctx.bot.d.con
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, manga_name, guild_channel, latest_chapter FROM manga"
        )
        rows = cursor.fetchall()
        print(rows)
        rows.insert(0, ("ID", "Name", "Channel", "Ch"))

        output = tabulate(rows, headers="firstrow")

        await ctx.respond(f"Subscriptions: \n{output}")
    except Exception as e:
        print(e)


def check_mangasee(link: str) -> bool:
    if "https://mangasee123.com/manga/" in link:
        series_name = link.split("https://mangasee123.com/manga/")[1]
        if requests.get(f"https://mangasee123.com/rss/{series_name}.xml").ok:
            return True
        else:
            return False
    else:
        return False


@updates.command
@lb.add_checks()
@lb.option(
    "message",
    "Custom message to send with the update",
    str,
    required=False,
    modifier=lb.OptionModifier.CONSUME_REST,
)
@lb.option(
    "channel", "The channel to send updates in", hk.GuildTextChannel, required=False
)
@lb.option("series", "The link of the series to subscribe", str)
@lb.command(
    "subscribe", "Subscribe to updates of a series", pass_options=True, aliases=["sub"]
)
@lb.implements(lb.PrefixCommand)
async def subscribe(
    ctx: lb.Context,
    series: str,
    channel: hk.GuildTextChannel = None,
    message: str = None,
) -> None:
    # Sample: https://mangasee123.com/manga/Oshi-no-Ko
    # Sample RSS: https://mangasee123.com/rss/Oshi-no-Ko.xml
    try:
        if not ctx.get_guild().id in [980479965726404670]:
            print("\n\n", ctx.get_guild().id, "\n\n")
            await ctx.respond("no")
            return

        if not check_mangasee(series):
            await ctx.respond("Invalid series.")
            return
        if not channel:
            channel = ctx.get_channel().id
        else:
            channel = channel.id

        series_name = series.split("https://mangasee123.com/manga/")
        db = ctx.bot.d.con
        cursor = db.cursor()
        url = f"https://mangasee123.com/rss/{series_name[1]}.xml"
        print(f"https://www.toptal.com/developers/feed2json/convert?url={url}")
        req = requests.get(
            f"https://www.toptal.com/developers/feed2json/convert?url={url}"
        )
        if req.ok:
            req = req.json()
        else:
            await ctx.respond("Error")
            print(req.json())
            return
        print(req)

        cursor.execute(
            """
        INSERT INTO manga (manga_name, manga_link, guild_id, guild_channel, latest_chapter, custom_text)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
            (
                req["title"],
                url,
                channel,
                ctx.get_channel().id,
                int(req["items"][0]["title"].split(" ")[-1]),
                message,
            ),
        )
        db.commit()
        await ctx.respond("Done")
    except Exception as e:
        print(e)


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(updates)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(updates)
