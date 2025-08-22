"""Seasonal anime releases feed"""
import asyncio
import re
from datetime import datetime, timezone

import hikari as hk
import lightbulb as lb
from dateutil import parser
from orjson import loads

from functions.buttons import GenericButton, NewButton
from functions.models import ColorPalette as colors
from functions.models import EmoteCollection as emotes
from functions.utils import rss2json
from functions.views import PeristentViewTest

aniupdates = lb.Plugin(
    "Anime Updates", "Keep a track of seasonal anime", include_datastore=True
)
aniupdates.d.help = False


async def _get_magnet_for(query: str):
    magnet_feed = "https://subsplease.org/rss/?r=1080"
    items = rss2json(magnet_feed)
    items = loads(items)

    for i in items["feeds"]:
        if i["title"] == query:
            return i["link"]


async def _get_anime_updates() -> list:
    # mag_feed = "https://subsplease.org/rss/?r=1080"
    link_feed = "https://subsplease.org/rss/?t&r=1080"

    items = rss2json(link_feed)
    items = loads(items)
    if not items["data"]["status"] == "ok":
        return []

    updates = []

    for i in items["feeds"]:
        item_dict = {}

        if (
            int(
                (
                    datetime.now(timezone.utc) - parser.parse(i["published"])
                ).total_seconds()
            )
            > 720
        ):
            # Series didn't release in the last 12 minutes, so continue to loop
            continue
        item_dict["timestamp"] = parser.parse(i["published"])
        item_dict["link"] = i["link"]
        item_dict["file"] = i["title"]
        item_dict["data"] = {}
        item_dict["data"] = await return_anime_info(
            i["title"][13:-13].split("(")[0][:-6]
        )
        if not item_dict["data"]:
            # Series not on AL, hence skipping it
            continue

        updates.append(item_dict)

    return updates


@aniupdates.listener(hk.StartedEvent)
async def on_starting(event: hk.StartedEvent) -> None:
    """Event fired on start of bot"""
    
    return
    view = PeristentViewTest()
    await view.start()

    while True:
        print("Getting anime updates")
        updates = await _get_anime_updates()
        if not updates:
            print("\n\nNOTHING\n\n")

        for update in updates:
            view = PeristentViewTest()
            view.add_item(
                NewButton(
                    style=hk.ButtonStyle.SECONDARY,
                    custom_id=f"{int(datetime.now().timestamp())}",
                    emoji=hk.Emoji.parse("🧲"),
                    link=await _get_magnet_for(update["file"]),
                )
            )
            view.add_item(
                GenericButton(
                    style=hk.ButtonStyle.SECONDARY,
                    emoji=hk.Emoji.parse(emotes.NYAA.value),
                    url=update["link"],
                )
            )
            view.add_item(
                GenericButton(
                    style=hk.ButtonStyle.LINK,
                    emoji=hk.Emoji.parse(emotes.AL.value),
                    url=update["data"]["siteUrl"],
                )
            )
            for channel in aniupdates.bot.d.config.get("UPDATE_CHANNELS", []):
                check = await aniupdates.bot.rest.create_message(
                    channel=channel,
                    embed=hk.Embed(
                        color=colors.ELECTRIC_BLUE,
                        description=update["file"][13:],
                        timestamp=update["timestamp"],
                        title=(
                            f"Episode {get_episode_number(update['file'])}: "
                            f"{update['data']['title']['romaji']} out"
                        ),
                    )
                    .add_field(
                        "Rating",
                        update.get("data", {}).get("meanScore", "NA"),
                        inline=True,
                    )
                    .add_field(
                        "Genres", ", ".join(update["data"]["genres"][:3]), inline=True
                    )
                    .set_footer("Via: SubsPlease.org")
                    .set_thumbnail(update["data"]["coverImage"]["extraLarge"]),
                    components=view,
                )
                await view.start(check)
        await asyncio.sleep(720)


async def return_anime_info(anime):
    query = """
  query ($search: String) { # Define which variables will be used (id)
    Media (search: $search, type: ANIME) { # The sort param was POPULARITY_DESC
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

    return (
        await (
            await aniupdates.bot.d.aio_session.post(
                "https://graphql.anilist.co",
                json={"query": query, "variables": variables},
                timeout=10,
            )
        ).json()
    )["data"]["Media"]


def get_episode_number(name):
    name = name[13:-23].split("-")[-1].strip()
    regex = r"(\d+)(v\d)?"

    ep = re.search(regex, name).group(1)

    if not ep:
        return 1

    return ep


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(aniupdates)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(aniupdates)
