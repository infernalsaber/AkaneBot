"""To make text or message logs"""
import os

import hikari as hk
import lightbulb as lb

import requests
import sqlite3

from dateutil import parser
import datetime

import miru 

import asyncio

from functions.utils import CustomNavi, rss2json
from functions.buttons import GenericButton

import json

aniupdates = lb.Plugin("Anime Updates", "Keep a track of seasonal anime")


async def get_anime_updates() -> list:
    link = "https://www.toptal.com/developers/feed2json/convert"
    
    magnet_feed = "https://subsplease.org/rss/?r=1080"
    link_feed = "https://subsplease.org/rss/?t&r=1080"
    
    items = rss2json(link_feed)
    items = json.loads(items)
    if not items['data']['status'] == 'ok':
        return []
    # print(items)

    updates = []

    # print(items.keys())
    for i in items['feeds']:
        item_dict = {}
        if not '1080' in i['title']:
            continue
        # print("\n")
        print(datetime.datetime.now(datetime.timezone.utc))
        print(i['title'])
        print(i['published'])
        # print(parser.parse(i['date_published']))
        # print((datetime.datetime.now(datetime.timezone.utc)-parser.parse(i['date_published'])))
        # print(int((datetime.datetime.now(datetime.timezone.utc)-parser.parse(i['date_published'])).total_seconds()) )
        
        # try:
        if int((datetime.datetime.now(datetime.timezone.utc)-parser.parse(i['published'])).total_seconds()) > 720:
            print("short")
            continue
        item_dict['timestamp'] = parser.parse(i['published'])
        item_dict['link'] = i['link']
        item_dict['file']  = i['title']
        item_dict['data'] = {}
        item_dict['data'] = return_anime_info(i['title'][13:-13].split('(')[0][:-6])
        if not item_dict['data']:
            print("Not on AL")
            continue
        print(item_dict)
        updates.append(item_dict)

        # except Exception as e:
        #     print(e)
    return updates





@aniupdates.listener(hk.StartedEvent)
async def on_starting(event: hk.StartedEvent) -> None:
    """Event fired on start of bot"""
    conn = sqlite3.connect('akane_db.db')
    cursor = conn.cursor()
    aniupdates.bot.d.con = conn
    
#     cursor.execute('''
#     CREATE TABLE IF NOT EXISTS aniupdates (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         guild_channel INTEGER,
#     )
# ''')


    while True:
        print("Getting anime updates")
        updates = await get_anime_updates()
        if not updates:
            print("\n\nNOTHING\n\n")
        # print(updates)
        for update in updates:
            view = miru.View()
            view.add_item(GenericButton(
                style=hk.ButtonStyle.LINK, 
                # label = "Nyaa",
                emoji=hk.Emoji.parse("<:nyaasi:1127717935968952440>"),
                url = update['link'])
            )
            view.add_item(GenericButton(
                style=hk.ButtonStyle.LINK, 
                # label = "Anilist",
                emoji=hk.Emoji.parse("<:anilist:1127683041372942376>"),
                url = update['data']['siteUrl'])
            )
            for channel in aniupdates.bot.d.update_channels:
                await aniupdates.bot.rest.create_message(
                    channel=channel,
                    # content=update,
                    embed=hk.Embed(
                        color=0x7DF9FF,
                        description=update['file'],
                        timestamp=update['timestamp'],
                        title=f"New Episode of {update['data']['title']['romaji']} out",
                        url=update['link']
                    )
                    .add_field("Episode", get_episode_number(update['file']))
                    # .add_field("Filler", "This is some random filler text to take the space")
                    # .add_field("🧲", f"```{update['url']}```")
                    # .set_author(
                    #     name=f"New Episode of {update['data']['title']['romaji']} out",
                    #     url=update['data']['siteUrl']
                    # )
                    .set_thumbnail(update['data']['coverImage']['extraLarge']),
                    components=view
                )
        await asyncio.sleep(720)






def return_anime_info(anime):
  query = """
  query ($search: String) { # Define which variables will be used (id)
    Media (search: $search, type: ANIME, status: RELEASING) { # The sort param was POPULARITY_DESC
      id
      title {
          english
          romaji
      }
      coverImage {
          extraLarge
      }
      description (asHtml: false)
      siteUrl
    }
  }

  """

  variables = {"search": anime}

  return requests.post(
    "https://graphql.anilist.co",
    json={"query": query, "variables": variables},
    timeout=10,
  ).json()['data']['Media']


def get_episode_number(name):
    num = name[13:-23].split("-")[-1].strip()
    try:
        num = int(num)
    except:
        num = 1
    return num


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(aniupdates)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(aniupdates)