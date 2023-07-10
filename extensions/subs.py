"""To make text or message logs"""
import os

import hikari as hk
import lightbulb as lb

import requests
import sqlite3

updates = lb.Plugin("Log Commands", "Keeping a log of data, more to be added later")


@updates.listener(hk.StartingEvent)
async def on_starting(event: hk.StartingEvent) -> None:
    """Event fired on start of bot"""
    return
#     conn = sqlite3.connect('manga_database.db')
#     cursor = conn.cursor()
#     updates.bot.d.con = conn
    
#     cursor.execute('''
#     CREATE TABLE IF NOT EXISTS manga (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         manga_name TEXT,
#         manga_link TEXT,
#         guild_id INTEGER,
#         guild_channel INTEGER,
#         latest_chapter INTEGER
#     )
# ''')

#     updates.bot.rest.create_message()



# @updates.listener(hk.StoppingEvent)
# async def on_stopping(event: hk.StoppingEvent) -> None:
#     """Event fired on stopping the bot"""
#     updates.bot.d.db.close()
    






# @updates.command
# @lb.add_checks()
# @lb.command("subscriptions", "Send server manga subscriptions", pass_options=True)
# @lb.implements(lb.PrefixCommand)
# async def subs(ctx: lb.Context) -> None:
#     """Send the log file folder as a .rar file"""

#     await ctx.respond("ok")
#     try:
#         if not ctx.get_guild().id in [980479965726404670]:
#             await ctx.respond("no")
#             return
#         db = ctx.bot.d.con
#         cursor = db.cursor()
#         cursor.execute('SELECT * FROM manga WHERE guild_id = ?', (ctx.get_guild().id,))
#         rows = cursor.fetchall()
#         print(rows)
#         output = ""
#         for i in rows:
#             output += i[1]
#             output += "\n"
#         await ctx.respond(f"Subscriptions: \n{output}")
#     except Exception as e:
#         print(e)
    
# def check_mangasee(link: str) -> bool:
#     if "https://mangasee123.com/manga/" in link:
#         series_name = link.split("https://mangasee123.com/manga/")
#         if requests.get(f"https://mangasee123.com/rss/{series_name}.xml").ok:
#             return True
#         else:
#             return False
#     else:
#         return False
    

# @updates.command
# @lb.add_checks()
# @lb.option(
#     "series", "The link of the series to subscribe", str
# )
# @lb.command("subscribe", "Subscribe to updates of a series", pass_options=True)
# @lb.implements(lb.PrefixCommand)
# async def subscribe(ctx: lb.Context, series: str) -> None:
#     """Send the latest log text file"""

#     # Sample: https://mangasee123.com/manga/Oshi-no-Ko
#     # Sample RSS: https://mangasee123.com/rss/Oshi-no-Ko.xml
#     try:
#         if not ctx.get_guild().id in [980479965726404670]:
#             print("\n\n",ctx.get_guild().id, "\n\n")
#             await ctx.respond("no")
#             return

#         # if not check_mangasee(series):
#         #     await ctx.respond("Invalid series.")
#         #     return
#         series_name = series.split("https://mangasee123.com/manga/")
#         db = ctx.bot.d.con
#         cursor = db.cursor()
#         url = f"https://mangasee123.com/rss/{series_name[1]}.xml"
#         print(f"https://www.toptal.com/developers/feed2json/convert?url={url}")
#         req = requests.get(f"https://www.toptal.com/developers/feed2json/convert?url={url}")
#         if req.ok:
#             req = req.json()
#         else:
#             await ctx.respond("Error")
#             print(req.json())
#             return
#         print(req)

#         cursor.execute('''
#         INSERT INTO manga (manga_name, manga_link, guild_id, guild_channel, latest_chapter)
#         VALUES (?, ?, ?, ?, ?)
#     ''', (req["title"], series, ctx.get_guild().id, ctx.get_channel().id, int(req["items"][0]["title"].split(" ")[-1])))
#         db.commit()
#         await ctx.respond("Done")
#     except Exception as e:
#         print(e)


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(updates)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(updates)