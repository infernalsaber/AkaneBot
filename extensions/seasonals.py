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

from functions.utils import CustomNavi
from functions.buttons import GenericButton



aniupdates = lb.Plugin("Anime Updates", "Keep a track of seasonal anime")


async def get_anime_updates() -> list:
    link = "https://www.toptal.com/developers/feed2json/convert"
    
    magnet_feed = "https://subsplease.org/rss/?r=1080"
    link_feed = "https://subsplease.org/rss/?t&r=1080"
    
    items = requests.get(link, params={"url": magnet_feed})
    if not items.ok:
        return []
    items = items.json()

    updates = []

    for i in items['items']:
        item_dict = {}
        if int((datetime.datetime.now(datetime.timezone.utc)-parser.parse(i['date_published'])).total_seconds()) > 900:
            continue
        item_dict['timestamp'] = parser.parse(i['date_published'])
        item_dict['url'] = i['url']
        item_dict['file']  = i['title']
        item_dict['data'] = {}
        item_dict['data'] = return_anime_info(i['title'][13:-13].split('(')[0][:-6])
        if not item_dict['data']:
            continue
        updates.append(item_dict)
    
    return updates





@aniupdates.listener(hk.StartedEvent)
async def on_starting(event: hk.StartedEvent) -> None:
    """Event fired on start of bot"""
    
    while True:
        print("Getting anime updates")
        updates = await get_anime_updates()
        if not updates:
            print("\n\nNOTHING\n\n")
        print(updates)
        for update in updates:
            view = miru.View()
            view.add_item(GenericButton(
                style=hk.ButtonStyle.LINK, 
                # label = "Nyaa",
                emoji=hk.Emoji.parse("<:nyaasi:1127717935968952440>"),
                url = update['url'])
            )
            view.add_item(GenericButton(
                style=hk.ButtonStyle.LINK, 
                # label = "Anilist",
                emoji=hk.Emoji.parse("<:anilist:1127683041372942376>"),
                url = update['data']['siteUrl'])
            )
            
            await aniupdates.bot.rest.create_message(
                channel=980479966389096460,
                # content=update,
                embed=hk.Embed(
                    color=0x7DF9FF,
                    description=update['file'],
                    timestamp=parser.parse(i['date_published'])
                )
                # .add_field("Filler", "This is some random filler text to take the space")
                # .add_field("🧲", f"```{update['url']}```")
                .set_author(
                    name=f"New Episode of {update['data']['title']['romaji']} out",
                    url=update['data']['siteUrl']
                )
                .set_thumbnail(update['data']['coverImage']['large']),
                components=view
            )
        await asyncio.sleep(900)






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
          large
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





def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(aniupdates)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(aniupdates)