"""The animanga related plugin"""
import datetime
import re

import hikari as hk
import lightbulb as lb
from miru.ext import nav

from extensions.ping import (
    CustomNavi,
    CustomNextButton,
    CustomPrevButton,
    CustomView,
    GenericButton,
    KillButton,
    KillNavButton,
    PreviewButton,
    TrailerButton,
)
from functions.errors import RequestsFailedError

from functions.utils import verbose_timedelta

al_listener = lb.Plugin(
    "Weeb", "Search functions for anime, manga and characters (with an easter egg)"
)

pattern = re.compile(r"\b(https?:\/\/)?(www.)?anilist.co\/(anime|manga)\/(\d{1,6})")
spoiler_str = re.compile(r"||")


def parse_description(description: str) -> str:
    description = (
        description.replace("<br>", "")
        .replace("~!", "||")
        .replace("!~", "||")
        .replace("#", "")
    )
    description = (
        description.replace("<i>", "")
        .replace("<b>", "")
        .replace("</b>", "")
        .replace("</i>", "")
        .replace("<BR>", "")
    )

    if len(description) > 400:
        description = description[0:400]

        # If the trimmed description has a missing spoiler tag, add one
        if description.count("||") % 2:
            description = description + "||"

        description = description + "..."

    return description


async def get_imp_info(chapters):
    """Parse the chapter info and return the required parts"""
    volume_last = list(chapters["volumes"].keys())[0]
    chapter_last = list(chapters["volumes"][volume_last]["chapters"].keys())[0]
    id_last = chapters["volumes"][volume_last]["chapters"][chapter_last]["id"]

    volume_first = list(chapters["volumes"].keys())[-1]
    chapter_first = list(chapters["volumes"][volume_first]["chapters"].keys())[-1]
    id_first = chapters["volumes"][volume_first]["chapters"][chapter_first]["id"]

    return {
        "latest": {"chapter": chapter_last, "id": id_last},
        "first": {"chapter": chapter_first, "id": id_first},
    }


@al_listener.command
@lb.option(
    "media",
    "The name of the media to search",
    modifier=lb.commands.OptionModifier.CONSUME_REST,
)
@lb.option(
    "type",
    "The type of media to search for",
    choices=["anime", "manga", "novel", "vn", "character"],
)
@lb.command(
    "lookup",
    "Look up anime/manga/character on anilist",
    pass_options=True,
    aliases=["lu"],
    auto_defer=True,
)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def al_search(ctx: lb.Context, type: str, media: str) -> None:
    """Search an anime/manga/character on AL"""

    print("Type is", type)

    if type.lower() in ["anime", "manga", "m", "a"]:
        if type[0].lower() == "m":
            await search_manga(ctx, media)
            return
        else:
            await search_anime(ctx, media)
            return

    elif type.lower() in ["character", "c"]:
        await search_character(ctx, media)
        return

    elif type.lower() in ["novel", "n"]:
        await search_novel(ctx, media)
        return

    elif type.lower() in ["vn", "visualnovel"]:
        await search_vn(ctx, media)
        return

    else:
        await ctx.respond(
            "Invalid media type. Please use `-help lookup` to see the options"
        )
        return


@al_listener.command
@lb.option("query", "The anime query", modifier=lb.commands.OptionModifier.CONSUME_REST)
@lb.command("anime", "Search a anime", pass_options=True, aliases=["ani", "a"])
@lb.implements(lb.PrefixCommand)
async def anime_search(ctx: lb.PrefixContext, query: str):
    await search_anime(ctx, query)


@al_listener.command
@lb.option("query", "The manga query", modifier=lb.commands.OptionModifier.CONSUME_REST)
@lb.command("manga", "Search a manga", pass_options=True, aliases=["m"])
@lb.implements(lb.PrefixCommand)
async def manga_search(ctx: lb.PrefixContext, query: str):
    await search_manga(ctx, query)


@al_listener.command
@lb.option(
    "user",
    "The user whose anilist is to be shown",
)
@lb.command("user", "Show a user's AL and stats", pass_options=True, aliases=["u"])
@lb.implements(lb.PrefixCommand)
async def user_al(ctx: lb.PrefixContext, user: str):
    await ctx.respond(f"https://anilist.co/user/{user}")


@al_listener.command
@lb.option("query", "The novel query", modifier=lb.commands.OptionModifier.CONSUME_REST)
@lb.command("novel", "Search a novel", pass_options=True, aliases=["novels", "n", "ln"])
@lb.implements(lb.PrefixCommand)
async def user_al(ctx: lb.PrefixContext, query: str):
    await search_novel(ctx, query)


@al_listener.command
@lb.option(
    "query", "The character query", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command(
    "character", "Search a character", pass_options=True, aliases=["chara", "c"]
)
@lb.implements(lb.PrefixCommand)
async def user_al(ctx: lb.PrefixContext, query: str):
    await search_character(ctx, query)


@al_listener.command
@lb.option(
    "filter",
    "Filter the type of anime to fetch",
    choices=["airing", "upcoming", "bypopularity", "favorite"],
    required=False,
)
@lb.command("top", "Find top anime on MAL", pass_options=True)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def topanime(ctx: lb.PrefixContext, filter: str = None):
    """Find the top anime on AL

    Args:
        ctx (lb.PrefixContext): The event context (irrelevant to the user)
        filter (str, optional): The search filter (top, airing, bypopularity)

    Raises:
        RequestsFailedError: Raised if the API call fails
    """

    num = 5
    if filter and filter in ["airing", "upcoming", "bypopularity", "favorite"]:
        params = {"limit": num, "filter": filter}
    else:
        params = {"limit": num}

    async with ctx.bot.d.aio_session.get(
        "https://api.jikan.moe/v4/top/anime", params=params, timeout=3
    ) as res:
        if res.ok:
            res = await res.json()
            embed = (
                hk.Embed(color=0x2E51A2)
                .set_author(name="Top Anime")
                .set_footer(
                    "Fetched via MyAnimeList.net",
                    icon="https://cdn.myanimelist.net/img/sp/icon/apple-touch-icon-256.png",
                )
            )

            for i, item in enumerate(res["data"]):
                embed.add_field(
                    f"{i+1}.",
                    f"```ansi\n\u001b[0;32m{item['rank'] or ''}. \u001b[0;36m{item['title']} \u001b[0;33m({item['score'] or item['members']})```",
                )

            await ctx.respond(embed=embed)
        else:
            raise RequestsFailedError


@al_listener.command
@lb.option(
    "query", "The vn to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("visualnovel", "Search a vn", pass_options=True, aliases=["vn"])
@lb.implements(lb.PrefixCommand)
async def vn_search(ctx: lb.PrefixContext, query: str):
    await search_vn(ctx, query)


@al_listener.command
@lb.option(
    "query", "The vn trait to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vntrait", "Search a vn", pass_options=True, aliases=["trait"])
@lb.implements(lb.PrefixCommand)
async def vn_search(ctx: lb.PrefixContext, query: str):
    await search_vntrait(ctx, query)


@al_listener.command
@lb.option(
    "query", "The vntag to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vntag", "Search a vntag", pass_options=True, aliases=["tag"])
@lb.implements(lb.PrefixCommand)
async def vn_search(ctx: lb.PrefixContext, query: str):
    await search_vntag(ctx, query)


@al_listener.command
@lb.option(
    "query", "The vnchara to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vnc", "Search a vn character", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def vn_search(ctx: lb.PrefixContext, query: str):
    await search_vnchara(ctx, query)


@al_listener.command
@lb.option("code", "You know it", int)
@lb.command("nh", "Search 🌚", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def nhhh(ctx: lb.PrefixContext, code: int):
    if not ctx.get_channel().is_nsfw:
        return

    res = await ctx.bot.d.aio_session.get(
        f"https://cubari.moe/read/api/nhentai/series/{code}/", timeout=3
    )
    if res.ok:
        res = await res.json()

        buttons = [
            CustomPrevButton(),
            nav.IndicatorButton(),
            CustomNextButton(),
            KillNavButton(),
        ]

        pages = []
        for i in res["chapters"]["1"]["groups"]["1"]:
            pages.append(
                hk.Embed(
                    title=res["title"],
                    url=f"https://nhentai.net/g/{res['slug']}",
                    description=f"Author: {res['author']} | Artist: {res['artist']}",
                ).set_image(i)
            )

        navigator = CustomNavi(
            pages=pages, buttons=buttons, timeout=180, user_id=ctx.author.id
        )
        await navigator.send(
            ctx.channel_id,
        )

    else:
        await ctx.respond("Didn't work")
        print(res.json())


@al_listener.command
@lb.add_checks(lb.owner_only)
@lb.option(
    "map", "The vnchara to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.option("person", "The vnchara to search")
@lb.command("addtrait", "Search a vn character", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def add_trait_map(ctx: lb.PrefixContext, person: str, map: str):
    try:
        db = ctx.bot.d.con
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO traitmap (user, trait) VALUES (?, ?)""",
            (person, map),
        )
        db.commit()
        await ctx.respond("Done")
    except Exception as e:
        print(e)


@al_listener.command
@lb.add_checks(lb.owner_only)
@lb.option("person", "The vnchara to search")
@lb.command("rmtrait", "Search a vn character", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def remove_trait_map(ctx: lb.PrefixContext, person: str):
    try:
        db = ctx.bot.d.con
        cursor = db.cursor()
        cursor.execute("DELETE FROM traitmap where user = ?", (person,))
        await ctx.respond("Removed trait")
        db.commit()
    except Exception as e:
        print(e)


async def fetch_trait_map(user):
    db = al_listener.bot.d.con
    cursor = db.cursor()
    cursor.execute("SELECT trait FROM traitmap WHERE user=?", (user,))
    return cursor.fetchone()


async def search_character(ctx: lb.Context, character: str):
    """Search a character on AL"""
    query = """
query ($id: Int, $search: String) { # Define which variables will be used in the query
  Character (id: $id, search: $search,  sort: FAVOURITES_DESC) { # Add var. to the query
    id
    name {
      full
    }
    image {
      large
    }
    gender
    dateOfBirth {
        year
        month
        day
    }
    description (asHtml: false)
    media (sort: TRENDING_DESC, perPage: 3) {
        nodes {
            title {
                romaji
                english
            }
            season
            seasonYear
            seasonInt
            episodes
            chapters
            source
            coverImage {
                large
            }
            popularity
            tags {
              name
            }
        }
    }
    favourites #♥
    siteUrl
  }
}
"""

    variables = {
        "search": character
        # ,"sort": FAVOURITES_DESC
    }

    response = await ctx.bot.d.aio_session.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": variables},
        timeout=3,
    )
    if not response.ok:
        await ctx.respond(
            f"Failed to fetch data 😵. \nTry typing the full name of the character."
        )
        return
    response = await response.json()

    response = response["data"]["Character"]

    title = response["name"]["full"]

    if response["dateOfBirth"]["month"] and response["dateOfBirth"]["day"]:
        dob = f"{response['dateOfBirth']['day']}/{response['dateOfBirth']['month']}"
        if response["dateOfBirth"]["year"]:
            dob += f"/{response['dateOfBirth']['year']}"
    else:
        dob = "NA"

    if response["description"]:
        response["description"] = parse_description(response["description"])

    else:
        response["description"] = "NA"

    try:
        view = CustomView(user_id=ctx.author.id)
        view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))

        choice = await ctx.respond(
            embed=hk.Embed(
                description="\n\n",
                color=0x2B2D42,
                timestamp=datetime.datetime.now().astimezone(),
            )
            .add_field("Gender", response["gender"])
            .add_field("DOB", dob, inline=True)
            .add_field("Favourites", f"{response['favourites']}❤", inline=True)
            .add_field("Character Description", response["description"])
            .set_thumbnail(response["image"]["large"])
            .set_author(url=response["siteUrl"], name=title)
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            ),
            components=view,
        )
        await view.start(choice)
        await view.wait()

        if hasattr(view, "answer"):  # Check if there is an answer
            print(f"Received an answer! It is: {view.answer}")
        else:
            await ctx.edit_last_response(components=[])
    except Exception as e:
        print(e)
    return


async def search_novel(ctx: lb.Context, novel: str):
    query = """
query ($id: Int, $search: String, $type: MediaType) { # Define which variables will be used in the query (id)
  Media (id: $id, search: $search, type: $type, sort: POPULARITY_DESC, format_in: [NOVEL]) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
    id
    idMal
    title {
        english
        romaji
    }
    type
    averageScore
    format
    meanScore
    chapters
    episodes
    startDate {
        year
    }
    coverImage {
        large
    }
    bannerImage
    genres
    status
    description (asHtml: false)
    siteUrl
  }
}

"""
    print("\n\nNOVEL SEARCH\n\n")
    variables = {"search": novel, "type": "MANGA"}

    response = await ctx.bot.d.aio_session.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": variables},
        timeout=3,
    )

    if not response.ok:
        await ctx.respond(
            f"Failed to fetch data 😵, error `code: {response.status_code}`"
        )
        return
    response = (await response.json())["data"]["Media"]

    title = response["title"]["english"] or response["title"]["romaji"]

    no_of_items = response["chapters"] or response["episodes"] or "NA"

    if response["description"]:
        response["description"] = parse_description(response["description"])

    else:
        response["description"] = "NA"

    # try:
    view = CustomView(user_id=ctx.author.id)
    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
    choice = await ctx.respond(
        embed=hk.Embed(
            description="\n\n",
            color=0x2B2D42,
            timestamp=datetime.datetime.now().astimezone(),
        )
        .add_field("Rating", response["meanScore"])
        .add_field("Genres", ", ".join(response["genres"][:4]))
        .add_field("Status", response["status"], inline=True)
        .add_field(
            "Volumes",
            no_of_items,
            inline=True,
        )
        .add_field("Summary", response["description"])
        .set_thumbnail(response["coverImage"]["large"])
        .set_image(response["bannerImage"])
        .set_author(url=response["siteUrl"], name=title)
        .set_footer(
            text="Source: AniList",
            icon="https://anilist.co/img/icons/android-chrome-512x512.png",
        ),
        components=view,
    )

    await view.start(choice)
    await view.wait()

    if hasattr(view, "answer"):  # Check if there is an answer
        print(f"Received an answer! It is: {view.answer}")
    else:
        await ctx.edit_last_response(components=[])


async def search_anime(ctx, anime: str):
    query = """
query ($id: Int, $search: String, $type: MediaType) { # Define which variables will be used (id)
  Page (perPage: 5) {
  media (id: $id, search: $search, type: $type) { # The sort param was POPULARITY_DESC
    id
    idMal
    title {
        english
        romaji
    }
    duration
    type
    averageScore
    format
    meanScore
    episodes
    startDate {
        year
    }
    coverImage {
        large
    }
    bannerImage
    genres
    status
    description (asHtml: false)
    siteUrl
    trailer {
        id
        site
        thumbnail
    }
  }
  }
}

"""

    variables = {"search": anime, "type": "ANIME"}

    response = await ctx.bot.d.aio_session.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": variables},
        timeout=3,
    )

    if not response.ok or not len((await response.json())["data"]["Page"]["media"]):
        await ctx.respond(
            f"Failed to fetch data 😵, error `code: {response.status_code}`"
        )
        return

    num = 0
    if not len((await response.json())["data"]["Page"]["media"]) == 1:
        view = CustomView(user_id=ctx.author.id)
        embed = hk.Embed(
            title="Choose the desired anime",
            color=0x43408A,
            timestamp=datetime.datetime.now().astimezone(),
        )

        for count, item in enumerate((await response.json())["data"]["Page"]["media"]):
            embed.add_field(
                count + 1, item["title"]["english"] or item["title"]["romaji"]
            )
            view.add_item(
                GenericButton(style=hk.ButtonStyle.PRIMARY, label=f"{count+1}")
            )

        try:
            embed.set_image("https://i.imgur.com/FCxEHRN.png")
        except Exception as e:
            print(e)

        choice = await ctx.respond(embed=embed, components=view)

        await view.start(choice)
        await view.wait()

        if hasattr(view, "answer"):  # Check if there is an answer
            print(f"Received an answer! It is: {view.answer}")
            num = f"{view.answer}"

        else:
            await ctx.edit_last_response(views=[])
            return

        num = int(num) - 1

    response = (await response.json())["data"]["Page"]["media"][num]

    title = response["title"]["english"] or response["title"]["romaji"]

    no_of_items = (
        response["episodes"]
        if response["episodes"] != 1
        else verbose_timedelta(datetime.timedelta(minutes=response["duration"]))
    )

    if response["description"]:
        response["description"] = parse_description(response["description"])

    else:
        response["description"] = "NA"
    print("response parsed ig")

    try:
        view = CustomView(user_id=ctx.author.id)

        trailer = "Couldn't find anything."

        embed = (
            hk.Embed(
                description="\n\n",
                color=0x2B2D42,
                timestamp=datetime.datetime.now().astimezone(),
            )
            .add_field("Rating", response["meanScore"] or "NA")
            .add_field("Genres", ", ".join(response["genres"][:4]))
            .add_field("Status", response["status"].replace("_", " "), inline=True)
            .add_field(
                "Episodes" if response["episodes"] != 1 else "Duration",
                no_of_items,
                inline=True,
            )
            .add_field("Summary", response["description"])
            .set_thumbnail(response["coverImage"]["large"])
            .set_image(response["bannerImage"])
            .set_author(url=response["siteUrl"], name=title)
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        )
        if response["trailer"]:
            if response["trailer"]["site"] == "youtube":
                trailer = f"https://{response['trailer']['site']}.com/watch?v={response['trailer']['id']}"
            else:
                trailer = f"https://{response['trailer']['site']}.com/video/{response['trailer']['id']}"

            view.add_item(TrailerButton(trailer=trailer, other_page=embed))

        view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))

        await ctx.edit_last_response(
            embed=embed,
            components=view,
        )
        await view.start(choice)
        await view.wait()
    except Exception as e:
        print(e)
    trailer = "Couldn't find anything."

    if response["trailer"]:
        if response["trailer"]["site"] == "youtube":
            trailer = f"https://{response['trailer']['site']}.com/watch?v={response['trailer']['id']}"
        else:
            trailer = f"https://{response['trailer']['site']}.com/video/{response['trailer']['id']}"

        buttons = [TrailerButton(trailer=trailer, other_page=pages), KillNavButton()]
    else:
        buttons = [KillNavButton()]

    navigator = CustomNavi(
        pages=pages, buttons=buttons, timeout=180, user_id=ctx.author.id
    )


async def search_manga(ctx, manga: str):
    query = """
query ($id: Int, $search: String, $type: MediaType) { # Define which variables will be used in the query (id)
    Media (id: $id, search: $search, type: $type, sort: POPULARITY_DESC, format_in: [MANGA, ONE_SHOT]) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
        id
        idMal
        title {
            english
            romaji
        }
        type
        averageScore
        format
        meanScore
        chapters
        episodes
        startDate {
            year
        }
        coverImage {
            large
        }
        bannerImage
        genres
        status
        description (asHtml: false)
        siteUrl
    }
    }
"""

    variables = {"search": manga, "type": "MANGA"}

    response = await ctx.bot.d.aio_session.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": variables},
        timeout=3,
    )

    if not response.ok:
        await ctx.respond(
            f"Failed to fetch data 😵, error `code: {response.status_code}`"
        )
        return

    response = (await response.json())["data"]["Media"]
    print(response)

    title = response["title"]["english"] or response["title"]["romaji"]

    no_of_items = response["chapters"] or response["episodes"] or "NA"

    if response["description"]:
        response["description"] = parse_description(response["description"])

    else:
        response["description"] = "NA"
    print("response parsed ig")

    print("\n\nUsing MD\n\n")
    base_url = "https://api.mangadex.org"

    order = {
        "rating": "desc",
        "followedCount": "desc",
    }

    final_order_query = {}

    for key, value in order.items():
        final_order_query[f"order[{key}]"] = value

    req = await ctx.bot.d.aio_session.get(
        f"{base_url}/manga",
        params={**{"title": title}, **final_order_query},
        timeout=3,
    )

    if req.ok:
        try:
            manga_id = (await req.json())["data"][0]["id"]

            languages = ["en"]

            req = await ctx.bot.d.aio_session.get(
                f"{base_url}/manga/{manga_id}/aggregate",
                params={"translatedLanguage[]": languages},
                timeout=3,
            )

            data = await get_imp_info(await req.json())

            if no_of_items == "NA":
                no_of_items = (
                    f"[{data['latest']['chapter'].split('.')[0]}]("
                    f"https://cubari.moe/read/mangadex/{manga_id})"
                )
            else:
                no_of_items = (
                    f"[{no_of_items}](https://cubari.moe/read/mangadex/{manga_id})"
                )
        except:
            no_of_items = "NA"
    else:
        no_of_items = "NA"

    try:
        pages = [
            hk.Embed(
                description="\n\n",
                color=0x2B2D42,
                timestamp=datetime.datetime.now().astimezone(),
            )
            .add_field("Rating", response["meanScore"] or "NA")
            .add_field("Genres", ", ".join(response["genres"][:4]) or "NA")
            .add_field("Status", response["status"] or "NA", inline=True)
            .add_field(
                "Chapters" if response["type"] == "MANGA" else "Episodes",
                no_of_items or "NA",
                inline=True,
            )
            .add_field("Summary", response["description"] or "NA")
            .set_thumbnail(response["coverImage"]["large"])
            .set_image(response["bannerImage"])
            .set_author(url=response["siteUrl"], name=title)
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        ]

        buttons = [PreviewButton(), KillNavButton()]

        navigator = CustomNavi(
            pages=pages, buttons=buttons, timeout=180, user_id=ctx.author.id
        )
    except Exception as e:
        print(e)

    if isinstance(ctx, lb.SlashContext):
        await navigator.send(ctx.interaction, responded=True)
    else:
        await navigator.send(
            ctx.channel_id,
        )

    print("NavigatoID", navigator.message_id)
    ctx.bot.d.chapter_info[navigator.message_id] = [
        base_url,
        data["first"]["id"],
        title,
        manga_id,
        response["coverImage"]["large"],
        pages,
    ]


async def search_vn(ctx: lb.Context, query: str):
    url = "https://api.vndb.org/kana/vn"
    headers = {"Content-Type": "application/json"}
    data = {
        "filters": ["search", "=", query],
        "fields": "title, image.url, rating, released, length_minutes, description, tags.name",
        # "sort": "title"
    }
    try:
        req = await ctx.bot.d.aio_session.post(
            url, headers=headers, json=data, timeout=3
        )

        print(req)
        if not req.ok:
            await ctx.respond("Couldn't find the VN you asked for.")
            return

        print(await req.json())
        req = await req.json()

        print(list(tag["name"] for tag in req["results"][0]["tags"])[:3])
        if req["results"][0]["description"]:
            description = parse_vndb_desciption(req["results"][0]["description"])
        else:
            description = "NA"
        view = CustomView(user_id=ctx.author.id)
        view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
        choice = await ctx.respond(
            hk.Embed(color=0x948782, timestamp=datetime.datetime.now().astimezone())
            .add_field("Rating", req["results"][0]["rating"] or "NA")
            .add_field(
                "Tags",
                ", ".join(list(tag["name"] for tag in req["results"][0]["tags"])[:4])
                or "NA",
            )
            .add_field(
                "Released", req["results"][0]["released"] or "Unreleased", inline=True
            )
            .add_field(
                "Est. Time",
                verbose_timedelta(
                    datetime.timedelta(minutes=req["results"][0]["length_minutes"])
                )
                # f"{req['results'][0]['length_minutes']//60}h{req['results'][0]['length_minutes']%60}m"
                if req["results"][0]["length_minutes"] else "NA",
                inline=True,
            )
            .add_field("Summary", description)
            .set_thumbnail(req["results"][0]["image"]["url"])
            .set_author(
                name=req["results"][0]["title"],
                url=f"https://vndb.org/{req['results'][0]['id']}",
            )
            .set_footer(text="Source: VNDB", icon="https://s.vndb.org/s/angel-bg.jpg"),
            components=view,
        )
        await view.start(choice)
        await view.wait()

        if hasattr(view, "answer"):  # Check if there is an answer
            print(f"Received an answer! It is: {view.answer}")
        else:
            await ctx.edit_last_response(components=[])
    except Exception as e:
        print(e, "\n\n\n")


def replace_bbcode_with_markdown(match):
    url = match.group(1)
    link_text = match.group(2)
    markdown_link = f"[{link_text}]({url})"
    return markdown_link


def parse_vndb_desciption(description: str) -> str:
    description = (
        description.replace("[spoiler]", "||")
        .replace("[/spoiler]", "||")
        .replace("#", "")
        .replace("[i]", "")
        .replace("[b]", "")
        .replace("[/b]", "")
        .replace("[/i]", "")
    )

    print("\n\n\n", description, "\n\n\n")

    if "[url=/" in description:
        print("ok")
    description.replace("[url=/", "[url=https://vndb.org/")
    if "[url=/" in description:
        print("why ")

    print(description)

    pattern = r"\[url=(.*?)\](.*?)\[/url\]"

    # Replace BBCode links with Markdown links in the text
    description = re.sub(pattern, replace_bbcode_with_markdown, description)

    if len(description) > 300:
        description = description[0:300]

        if description.count("||") % 2:
            description = description + "||"

        description = description + "..."

    return description


async def search_vnchara(ctx: lb.Context, query: str):
    url = "https://api.vndb.org/kana/character"
    headers = {"Content-Type": "application/json"}
    data = {
        "filters": ["search", "=", query],
        "fields": "name, description, age, sex,  image.url, traits.name",
    }

    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data, timeout=3)

    if not req.ok:
        await ctx.respond("Couldn't find the tag you asked for.")
        return

    req = await req.json()

    if req["results"][0]["description"]:
        description = parse_vndb_desciption(req["results"][0]["description"])
    else:
        description = "NA"

    view = CustomView(user_id=ctx.author.id)
    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))

    choice = await ctx.respond(
        hk.Embed(color=0x948782, timestamp=datetime.datetime.now().astimezone())
        .add_field("Sex", req["results"][0]["sex"][0].upper() or "NA", inline=True)
        .add_field("Age", req["results"][0]["age"] or "NA", inline=True)
        .add_field(
            "Traits",
            ", ".join(list(trait["name"] for trait in req["results"][0]["traits"])[:4])
            or "NA",
        )
        .add_field("Summary", description)
        .set_thumbnail(req["results"][0]["image"]["url"])
        .set_author(
            name=req["results"][0]["name"],
            url=f"https://vndb.org/{req['results'][0]['id']}",
        )
        .set_footer(text="Source: VNDB", icon="https://files.catbox.moe/3gg4nn.jpg"),
        components=view,
    )
    await view.start(choice)
    await view.wait()

    if hasattr(view, "answer"):  # Check if there is an answer
        print(f"Received an answer! It is: {view.answer}")
    else:
        await ctx.edit_last_response(components=[])


async def search_vntag(ctx: lb.Context, query: str):
    url = "https://api.vndb.org/kana/tag"
    headers = {"Content-Type": "application/json"}
    data = {
        "filters": ["search", "=", query],
        "fields": "name, aliases, description, category, vn_count"
        # "sort": "title"
    }
    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data, timeout=3)

    if not req.ok:
        await ctx.respond("Couldn't find the tag you asked for.")
        return

    req = await req.json()

    if req["results"][0]["description"]:
        description = parse_vndb_desciption(req["results"][0]["description"])
    else:
        description = "NA"

    tags = ", ".join(req["results"][0]["aliases"]) or "NA"

    view = CustomView(user_id=ctx.author.id)
    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
    choice = await ctx.respond(
        hk.Embed(color=0x948782, timestamp=datetime.datetime.now().astimezone())
        .add_field("Aliases", tags)
        .add_field("Category", req["results"][0]["category"].upper(), inline=True)
        .add_field("No of VNs", req["results"][0]["vn_count"], inline=True)
        .add_field("Summary", description)
        .set_author(
            name=req["results"][0]["name"],
            url=f"https://vndb.org/{req['results'][0]['id']}",
        )
        .set_footer(text="Source: VNDB", icon="https://files.catbox.moe/3gg4nn.jpg"),
        components=view,
    )
    await view.start(choice)
    await view.wait()

    if hasattr(view, "answer"):  # Check if there is an answer
        print(f"Received an answer! It is: {view.answer}")
    else:
        await ctx.edit_last_response(components=[])


async def search_vntrait(ctx: lb.Context, query: str):
    url = "https://api.vndb.org/kana/trait"
    headers = {"Content-Type": "application/json"}

    if ctx.guild_id == 695200821910044783:
        db_check = await fetch_trait_map(query.lower())

        if db_check is not None:
            query = db_check[0]

    data = {
        "filters": ["search", "=", query],
        "fields": "name, aliases, description, group_name, char_count"
        # "sort": "title"
    }

    print("Query is", query)

    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data, timeout=3)

    if not req.ok:
        await ctx.respond("Couldn't find the tag you asked for.")
        return

    req = await req.json()

    if req["results"][0]["description"]:
        description = parse_vndb_desciption(req["results"][0]["description"])
    else:
        description = "NA"

    tags = ", ".join(req["results"][0]["aliases"][:5]) or "NA"

    view = CustomView(user_id=ctx.author.id)
    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
    choice = await ctx.respond(
        hk.Embed(color=0x948782, timestamp=datetime.datetime.now().astimezone())
        .add_field("Aliases", tags)
        .add_field("Group Name", req["results"][0]["group_name"], inline=True)
        .add_field("No of Characters", req["results"][0]["char_count"], inline=True)
        .add_field("Summary", description)
        .set_author(
            name=req["results"][0]["name"],
            url=f"https://vndb.org/{req['results'][0]['id']}",
        )
        .set_footer(text="Source: VNDB", icon="https://files.catbox.moe/3gg4nn.jpg"),
        components=view,
    )
    await view.start(choice)
    await view.wait()

    if hasattr(view, "answer"):  # Check if there is an answer
        print(f"Received an answer! It is: {view.answer}")
    else:
        await ctx.edit_last_response(components=[])


@al_listener.listener(hk.StartedEvent)
async def on_starting(event: hk.StartedEvent) -> None:
    """Event fired on start of bot"""

    # asyncio.sleep(0.5)
    conn = al_listener.bot.d.con
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS traitmap (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        trait TEXT
    )
"""
    )
    conn.commit()


@al_listener.set_error_handler
async def al_error_handler(event: lb.CommandErrorEvent) -> bool:
    """Exception handler"""
    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, RequestsFailedError):
        await event.context.respond(
            "The application failed to fetch a response", flags=hk.MessageFlag.EPHEMERAL
        )

    return False


@al_listener.listener(hk.ReactionAddEvent)
async def al_link_finder(event: hk.ReactionAddEvent) -> None:
    """Check if a message contains an animanga link and display it's info"""

    try:
        channel = await al_listener.bot.rest.fetch_channel(event.channel_id)
        message = await al_listener.bot.rest.fetch_message(
            event.channel_id, event.message_id
        )
        if not event.emoji_name == "🔍":
            return
        list_of_series = pattern.findall(message.content) or []
    except Exception as e:
        print(e)

    if len(list_of_series) != 0:
        await channel.send("Beep, bop. AniList link found")
        # await al_listener.bot.rest.edit_message(
        #     event.channel_id, event.message, flags=hk.MessageFlag.SUPPRESS_EMBEDS
        # )

        for series in list_of_series:
            query = """
query ($id: Int, $search: String, $type: MediaType) { # Define which variables will be used in the query (id)
  Media (id: $id, search: $search, type: $type, sort: POPULARITY_DESC) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
    id
    idMal
    title {
        english
        romaji
    }
    type
    averageScore
    format
    meanScore
    chapters
    episodes
    startDate {
        year
    }
    coverImage {
        large
    }
    bannerImage
    genres
    status
    description (asHtml: false)
    siteUrl
  }
}

"""

            variables = {"id": series[3], "type": series[2].upper()}

            response = await al_listener.bot.d.aio_session.post(
                "https://graphql.anilist.co",
                json={"query": query, "variables": variables},
                timeout=10,
            )
            if not response.ok:
                print(response.json())
                await event.message.respond(
                    f"Nvm 😵, error `code: {response.status_code}`"
                )
                return
            response = (await response.json())["data"]["Media"]

            title = response["title"]["english"] or response["title"]["romaji"]

            no_of_items = response["chapters"] or response["episodes"] or "NA"

            await channel.send(
                content="Here are it's details",
                embed=hk.Embed(
                    description="\n\n",
                    color=0x2B2D42,
                    timestamp=datetime.datetime.now().astimezone(),
                )
                .add_field("Rating", response["averageScore"])
                .add_field("Genres", ",".join(response["genres"]))
                .add_field("Status", response["status"], inline=True)
                .add_field(
                    "Chapters" if response["type"] == "MANGA" else "ANIME",
                    no_of_items,
                    inline=True,
                )
                .add_field(
                    "Summary",
                    f"{response['description'][0:250].replace('<br>', '') if len(response['description']) > 250 else response['description'].replace('<br>', '')}...",
                )
                .set_thumbnail(response["coverImage"]["large"])
                .set_image(response["bannerImage"])
                .set_author(url=response["siteUrl"], name=title)
                .set_footer(
                    text="Source: AniList",
                    icon="https://anilist.co/img/icons/android-chrome-512x512.png",
                ),
            )


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(al_listener)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(al_listener)
