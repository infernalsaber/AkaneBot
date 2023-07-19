"""To make text or message logs"""
import asyncio
import datetime
import json
import re

import hikari as hk
import lightbulb as lb
import requests
from dateutil import parser

from extensions.ping import GenericButton, NewButton, PeristentViewTest, rss2json

aniupdates = lb.Plugin("Anime Updates", "Keep a track of seasonal anime")


async def get_magnet_for(query: str):
    magnet_feed = "https://subsplease.org/rss/?r=1080"
    items = rss2json(magnet_feed)
    items = json.loads(items)

    for i in items["feeds"]:
        if i["title"] == query:
            return i["link"]


async def get_anime_updates() -> list:
    link = "https://www.toptal.com/developers/feed2json/convert"

    # magnet_feed = "https://subsplease.org/rss/?r=1080"
    link_feed = "https://subsplease.org/rss/?t&r=1080"

    items = rss2json(link_feed)
    items = json.loads(items)
    if not items["data"]["status"] == "ok":
        return []

    updates = []

    for i in items["feeds"]:
        item_dict = {}
        # if not "1080" in i["title"]:
        #     continue

        print(datetime.datetime.now(datetime.timezone.utc))
        print(i["title"])
        print(i["published"])

        # try:
        if (
            int(
                (
                    datetime.datetime.now(datetime.timezone.utc)
                    - parser.parse(i["published"])
                ).total_seconds()
            )
            > 720
        ):
            print("short")
            continue
        item_dict["timestamp"] = parser.parse(i["published"])
        item_dict["link"] = i["link"]
        item_dict["file"] = i["title"]
        item_dict["data"] = {}
        item_dict["data"] = await return_anime_info(i["title"][13:-13].split("(")[0][:-6])
        if not item_dict["data"]:
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
    view = PeristentViewTest()
    await view.start()
    # conn = sqlite3.connect("akane_db.db")
    # cursor = conn.cursor()
    # aniupdates.bot.d.con = conn

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
            view = PeristentViewTest()
            view.add_item(
                NewButton(
                    style=hk.ButtonStyle.SECONDARY,
                    # label="🧲",
                    custom_id=f"{int(datetime.datetime.now().timestamp())}",
                    emoji=hk.Emoji.parse("🧲"),
                    link=await get_magnet_for(update["file"]),
                )
            )
            view.add_item(
                GenericButton(
                    style=hk.ButtonStyle.SECONDARY,
                    # label="🧲",
                    # custom_id=f"{int(datetime.datetime.now().timestamp())}",
                    emoji=hk.Emoji.parse("<:nyaasi:1127717935968952440>"),
                    url=update["link"],
                )
            )
            view.add_item(
                GenericButton(
                    style=hk.ButtonStyle.LINK,
                    # label = "Anilist",
                    emoji=hk.Emoji.parse("<:anilist:1127683041372942376>"),
                    url=update["data"]["siteUrl"],
                )
            )
            for channel in aniupdates.bot.d.update_channels:
                check = await aniupdates.bot.rest.create_message(
                    channel=channel,
                    # content=update,
                    embed=hk.Embed(
                        color=0x7DF9FF,
                        description=update["file"][13:],
                        timestamp=update["timestamp"],
                        title=f"Episode {get_episode_number(update['file'])}: {update['data']['title']['romaji']} out",
                        # url=update["link"],
                    )
                    .add_field(
                        "Rating", update["data"]["meanScore"] or "NA", inline=True
                    )
                    .add_field(
                        "Genres", ", ".join(update["data"]["genres"][:3]), inline=True
                    )
                    .set_footer("Via: SubsPlease.org")
                    # .add_field("Episode", get_episode_number(update["file"]))
                    # .add_field("Filler", "This is some random filler text to take the space")
                    # .add_field("🧲", f"```{update['link']}```")
                    # .set_author(
                    #     name=f"New Episode of {update['data']['title']['romaji']} out",
                    #     url=update['data']['siteUrl']
                    # )
                    .set_thumbnail(update["data"]["coverImage"]["extraLarge"]),
                    components=view,
                )
                await view.start(check)
                # await view.wait()
        await asyncio.sleep(720)


async def return_anime_info(anime):
    query = """
  query ($search: String) { # Define which variables will be used (id)
    Media (search: $search, type: ANIME, sort: START_DATE_DESC) { # The sort param was POPULARITY_DESC
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
      meanScore
      genres
    }
  }

  """

    variables = {"search": anime}

    return (await (await aniupdates.bot.d.aio_session.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": variables},
        timeout=10,
    )).json())["data"]["Media"]


def get_episode_number(name):
    name = name[13:-23].split("-")[-1].strip()
    regex = "(\d+)(v\d)?"

    ep = re.search(regex, name).group(1)

    if not ep:
        return 1

    return ep
    # num = name[13:-23].split("-")[-1].strip()
    # try:
    #     num = int(num)
    # except:
    #     num = 1
    # return num


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(aniupdates)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(aniupdates)
