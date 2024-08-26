"""The animanga related plugin"""

import collections
import re
from datetime import datetime, timedelta
from operator import itemgetter
from typing import Optional

import hikari as hk
import lightbulb as lb
import miru
import pandas as pd
from curl_cffi import requests
from rapidfuzz import process
from rapidfuzz.fuzz import partial_ratio
from rapidfuzz.utils import default_process
from requests_html import HTMLSession

from functions import buttons as btns
from functions import views as views
from functions.components import CharacterSelect, SimpleTextSelect
from functions.errors import RequestsFailedError
from functions.models import ALCharacter
from functions.models import ColorPalette as colors
from functions.models import EmoteCollection as emotes
from functions.utils import verbose_date, verbose_timedelta

al_listener = lb.Plugin(
    "Lookup",
    "Search functions for anime, manga, characters and more",
    include_datastore=True,
)
al_listener.d.help_image = "https://i.imgur.com/2nEsM2W.png"
al_listener.d.help = True
al_listener.d.help_emoji = "🤔"


anilist_pattern = re.compile(
    r"\b(https?:\/\/)?(www.)?anilist.co\/(anime|manga)\/(\d{1,6})"
)
vndb_pattern = re.compile(r"\b(https?:\/\/)?(www.)?vndb.org\/[a-z]\/(\d+)")


def parse_description(description: str) -> str:
    """Parse Anilist descriptions into Discord friendly markdown

    Args:
        description (str): The description to parse

    Returns:
        str: The parsed description
    """

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
    first_chapter_dets = chapters["volumes"][volume_first]["chapters"][chapter_first]
    if "others" in first_chapter_dets.keys():
        id_first = first_chapter_dets["others"][0]
    else:
        id_first = first_chapter_dets["id"]

    return {
        "latest": {"chapter": chapter_last, "id": id_last},
        "first": {"chapter": chapter_first, "id": id_first},
    }


@al_listener.command
@lb.set_help(
    "### Search something on AL/VNDB (as applicable):"
    "\nOptions: \n**anime**: Anime from AL"
    "\n**manga**: Manga from AL (with preview)"
    "\n**novel**: Novel/Light Novel from AL"
    "\n**vn**: Visual Novel from VNDB"
    "\n**vnc**: VN character from VNDB"
    "\n**vntag**: VN Tag from VNDB"
    "\n**vntrait**: VN character trait from VNDB"
)
@lb.option(
    "media",
    "The name of the media to search",
    modifier=lb.commands.OptionModifier.CONSUME_REST,
)
@lb.option(
    "type",
    "The type of media to search for",
    choices=[
        "anime",
        "manga",
        "novel",
        "visual novel",
        "character",
        "vn trait",
        "vn tag",
        "vn character",
    ],
)
@lb.command(
    "lookup",
    "Find something on Anilist or VNDB",
    pass_options=True,
    aliases=["lu"],
    auto_defer=True,
)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def al_search(ctx: lb.Context, type: str, media: str) -> None:
    """A wrapper slash command for AL/VNDB search"""

    if isinstance(ctx, lb.PrefixContext):
        await ctx.respond(
            "Please note that the lookup prefix command is depreciated and due to be removed. "
            f"See the updated commands using `{ctx.prefix}help Lookup`."
            "\n(The capitalization is important)"
        )

    if type.lower() in ["anime", "manga", "m", "a"]:
        if type[0].lower() == "m":
            await _search_manga(ctx, media)
            return
        else:
            await _search_anime(ctx, media)
            return

    elif type.lower() in ["character", "c"]:
        await _search_characters(ctx, media)
        return

    elif type.lower() in ["novel", "n"]:
        await _search_novel(ctx, media)
        return

    elif type.lower() in ["vn", "visualnovel", "visual novel"]:
        await _search_vn(ctx, media)
        return

    elif type.lower() in ["vntrait", "trait", "vn trait"]:
        await _search_vntrait(ctx, media)
        return

    elif type.lower() in ["vntag", "tag", "vn tag"]:
        await _search_vntag(ctx, media)
        return

    elif type.lower() in ["vnc", "vncharacter", "vn character"]:
        await _search_vnchara(ctx, media)
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
    """Search an anime on AL

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The anime to search for
    """

    await _search_anime(ctx, query)


@al_listener.command
@lb.option("query", "The manga query", modifier=lb.commands.OptionModifier.CONSUME_REST)
@lb.command("manga", "Search a manga", pass_options=True, aliases=["m"])
@lb.implements(lb.PrefixCommand)
async def manga_search(ctx: lb.PrefixContext, query: str):
    """Search a manga on AL and fetch it's preview via MD

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The manga to search for
    """

    await _search_manga(ctx, query)


@al_listener.command
@lb.option(
    "user",
    "The user whose anilist is to be shown",
)
@lb.command("user", "Show a user's AL and stats", pass_options=True, aliases=["u"])
@lb.implements(lb.PrefixCommand)
async def user_al(ctx: lb.PrefixContext, user: str):
    """Shortcut for AL username

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The user
    """

    await ctx.respond(f"https://anilist.co/user/{user}")


@al_listener.command
@lb.option("query", "The novel query", modifier=lb.commands.OptionModifier.CONSUME_REST)
@lb.command("novel", "Search a novel", pass_options=True, aliases=["novels", "n", "ln"])
@lb.implements(lb.PrefixCommand)
async def ln_search(ctx: lb.PrefixContext, query: str):
    """Search a (light) novel on AL

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The novel to search for
    """

    await _search_novel(ctx, query)


@al_listener.command
@lb.set_help(
    "A simple character search from AL but with additional features.\n"
    "To filter a character by series, simply add a comma and the series name."
    "\nEg. `[p]c Ryou, Bocchi the Rock` will give you Ryou Yamada from the BTR"
    " series. \nIf you just enter `[p]c ,Bocchi the Rock` you'll get a dropdown of all "
    "characters from the series.\n"
    "Using `[p]c bday` (can also use birth or birthday) will show the character whose "
    "birthday it is today"
)
@lb.option(
    "query", "The character query", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command(
    "character", "Search a character", pass_options=True, aliases=["chara", "c"]
)
@lb.implements(lb.PrefixCommand)
async def chara_search(ctx: lb.PrefixContext, query: str):
    """Search a character on AL

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The character to search for
    """

    await _search_characters(ctx, query)


@al_listener.command
@lb.option(
    "filter",
    "Filter the type of anime to fetch",
    choices=["airing", "upcoming", "bypopularity", "favorite"],
    required=False,
)
@lb.command("top", "Find top anime on MAL", pass_options=True, auto_defer=True)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def topanime(ctx: lb.PrefixContext, filter: Optional[str] = None):
    """Find the top anime on AL

    Args:
        ctx (lb.PrefixContext): The event context (irrelevant to the user)
        filter (str, optional): The search filter (top, airing, bypopularity)

    Raises:
        RequestsFailedError: Raised if the API call fails
    """

    filtr = filter

    num = 5
    if filtr and filtr in ["upcoming", "bypopularity", "favorite"]:
        params = {"limit": num, "filter": filter}

    elif filtr in ["airing", "weekly", "week"]:
        url = "https://raw.githubusercontent.com/infernalsaber/Anicharts_API/main/anime_images.json"
        try:
            data = await (await ctx.bot.d.aio_session.get(url, timeout=3)).json()
            anitrendz = data[max(data.keys())]["anitrendz"]
            animecorner = data[max(data.keys())]["animecorner"]
        except Exception as e:
            await ctx.respond(f"parsing {e}")
            return
        try:
            pages = [
                hk.Embed(
                    title="Top 10 Anime of the Week: AniTrendz", color=colors.LILAC
                ).set_image(anitrendz["image_url"]),
                hk.Embed(
                    title="Top 10 Anime of the Week: AnimeCorner",
                    color=colors.LILAC,
                ).set_image(animecorner["image_url"]),
            ]
            view = views.AuthorView(user_id=ctx.author.id)
            view.add_item(
                btns.SwapButton(
                    emoji1=hk.Emoji.parse("<:next:1136984292921200650>"),
                    emoji2=hk.Emoji.parse("<:previous:1136984315415236648>"),
                    original_page=pages[0],
                    swap_page=pages[1],
                )
            )
            view.add_item(btns.KillButton())

            choice = await ctx.respond(
                embed=pages[0],
                components=view,
            )
            await view.start(choice)
            await view.wait()

            # if hasattr(view, "answer"):
            #     pass
            # else:
            #     await ctx.edit_last_response(components=[])

        except Exception as e:
            await ctx.respond(e)

        return

    else:
        params = {"limit": num}

    async with ctx.bot.d.aio_session.get(
        "https://api.jikan.moe/v4/top/anime", params=params, timeout=3
    ) as res:
        if res.ok:
            res = await res.json()
            embed = (
                hk.Embed(color=colors.MAL)
                .set_author(name="Top Anime")
                .set_footer(
                    "Fetched via MyAnimeList.net",
                    icon="https://cdn.myanimelist.net/img/sp/icon/apple-touch-icon-256.png",
                )
            )

            for i, item in enumerate(res["data"]):
                embed.add_field(
                    f"{i+1}.",
                    (
                        f"```ansi\n\u001b[0;32m{item['rank'] or ''}. \u001b[0;36m{item['title']}"
                        f" \u001b[0;33m({item['score'] or item['members']})```"
                    ),
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
    """Search for a visual novel via VNDB

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The vn to search for
    """

    await _search_vn(ctx, query)


@al_listener.command
@lb.option(
    "query", "The vn trait to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vntrait", "Search a vn", pass_options=True, aliases=["trait"])
@lb.implements(lb.PrefixCommand)
async def vn_trait_search(ctx: lb.PrefixContext, query: str):
    """Search for a visual novel character trait via VNDB

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The vn trait to search for
    """

    await _search_vntrait(ctx, query)


@al_listener.command
@lb.option(
    "query", "The vntag to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vntag", "Search a vntag", pass_options=True, aliases=["tag"])
@lb.implements(lb.PrefixCommand)
async def vn_tag_search(ctx: lb.PrefixContext, query: str):
    """Search for a visual novel tag via VNDB

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The vn tag to search for
    """

    await _search_vntag(ctx, query)


@al_listener.command
@lb.option(
    "query", "The vnchara to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vnc", "Search a vn character", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def vn_chara_search(ctx: lb.PrefixContext, query: str):
    """Search for a visual novel character via VNDB

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The character to search for
    """

    await _search_vnchara(ctx, query)


@al_listener.command
@lb.add_checks(lb.dm_only | lb.nsfw_channel_only)
@lb.option("code", "You know it", int)
@lb.command("nh", "Search 🌚", pass_options=True, hidden=True)
@lb.implements(lb.PrefixCommand)
async def nhhh(ctx: lb.PrefixContext, code: int):
    """Not gonna elaborate this one"""

    res = await ctx.bot.d.aio_session.get(
        f"https://cubari.moe/read/api/nhentai/series/{code}/", timeout=3
    )
    if res.ok:
        res = await res.json()

        pages = []
        for i in res["chapters"]["1"]["groups"]["1"]:
            pages.append(
                hk.Embed(
                    color=colors.HELL,
                    title=res["title"],
                    url=f"https://nhentai.net/g/{res['slug']}",
                    description=f"Author: {res['author']} | Artist: {res['artist']}",
                ).set_image(i)
            )

        navigator = views.AuthorNavi(pages=pages, timeout=180, user_id=ctx.author.id)
        await navigator.send(ctx.channel_id)

    else:
        await ctx.respond("Didn't work")
        print(res.json())


@al_listener.command
@lb.add_checks(lb.owner_only)
@lb.option(
    "map", "The vnchara to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.option("person", "The vnchara to search")
@lb.command("addtrait", "Add an alias for a vn trait ", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def add_trait_map(ctx: lb.PrefixContext, person: str, map: str):
    """Add an alias for a vn trait (fun command)"""
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
@lb.command("rmtrait", "Remove an alias for a vn trait", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def remove_trait_map(ctx: lb.PrefixContext, person: str):
    """Remove an alias for a vn trait (fun command)"""
    try:
        db = ctx.bot.d.con
        cursor = db.cursor()
        cursor.execute("DELETE FROM traitmap where user = ?", (person,))
        await ctx.respond("Removed trait")
        db.commit()
    except Exception as e:
        print(e)


@al_listener.command
@lb.add_checks(lb.owner_only)
@lb.command("traits", "Show all the traits")
@lb.implements(lb.PrefixCommand)
async def show_traits(ctx: lb.PrefixContext):
    """Show all the trait maps"""
    await ctx.respond(
        f'```{pd.read_sql("SELECT * FROM traitmap", ctx.bot.d.con).to_string(index=False)}```'
    )


@al_listener.command
@lb.option(
    "query", "The game to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("game", "Search a game on steam", pass_options=True, aliases=["steam"])
@lb.implements(lb.PrefixCommand)
async def game_search(ctx: lb.PrefixContext, query: str):
    """Search for a game on steam

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The vn trait to search for
    """

    # try:
    # resp = (await (await ctx.bot.d.aio_session.get(
    #     "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    #     ,
    #     timeout=10,
    # )).json())['applist']['apps']
    # await ctx.respond('Got the list of games')

    # resp = {v['name']: v['appid'] for v in resp}
    # names = list(resp.keys())
    # # await ctx.edit_last_response('revdict')

    # threshold = 70
    # name, confidence, _ = process.extractOne(query, names, processor=default_process, scorer=partial_ratio)
    # if confidence < threshold:
    #     await ctx.respond("No matches found")
    #     return
    # await ctx.edit_last_response("fuzz")

    session = HTMLSession()

    params = {
        "term": {query},
        "f": "games",
        "cc": "US",
        "realm": 1,
        "l": "english",
        "v": 22790766,
        "use_store_query": 1,
        "use_search_spellcheck": 1,
        "search_creators_and_tags": 1,
    }

    r = session.get("https://store.steampowered.com/search/suggest", params=params)
    # if r.ok:
    #     await ctx.respond(r.html.find('a')[0].attrs['href'])
    #     return
    # else:
    #     await ctx.respond("No matches found")
    #     return
    # resp = await ctx.bot.d.aio_session.get(
    #     f"https://store.steampowered.com/search/suggest?term={query}&f=games&cc=GB&realm=1&l=english&v=22790766&use_store_query=1&use_search_spellcheck=1&search_creators_and_tags=1",
    #     timeout=5,
    # )

    if not r.ok:
        await ctx.respond(
            hk.Embed(
                title="CAN'T FIND THE REQUESTED GAME",
                color=colors.ERROR,
                description="Your search failed to go through",
                timestamp=datetime.now().astimezone(),
            ),
            delete_after=15,
        )
        return

    # await ctx.respond("resp got")

    # soup = BeautifulSoup(resp, "lxml")
    # for a in soup.find_all('a'):
    # print(a.get('href'))
    # await ctx.respond(resp)
    sup = r.html.find("a")

    if not sup or len(sup) == 0:
        await ctx.respond(
            hk.Embed(
                title="CAN'T FIND THE REQUESTED GAME",
                color=colors.ERROR,
                description=f"Can't find the game `{query}`, maybe it's not on steam?",
                timestamp=datetime.now().astimezone(),
            ),
            delete_after=15,
        )
        return
    sup = sup[0].attrs["href"]
    # await ctx.edit_last_response("parseley")

    pattern = re.compile(r"https://store.steampowered.com/app/(\d+)")
    match = pattern.search(str(sup))

    if match:
        _id = match.group(1)
        resp = await ctx.respond(f"https://store.steampowered.com/app/{_id}")
    else:
        resp = await ctx.respond("No suitable game found")

    try:
        await (await resp.message()).add_reaction("❌")

        def predicate(event: hk.ReactionAddEvent) -> bool:
            return event.user_id == ctx.author.id and event.emoji_name == "❌"

        reaction = await ctx.bot.wait_for(
            hk.ReactionAddEvent, timeout=15 * 60, predicate=predicate
        )
        if reaction.emoji_name == "❌":
            await ctx.delete_last_response()
        else:
            pass

    except Exception:
        await (await resp.message()).remove_all_reactions()
    # TBA
    #     app_dets = (await (await ctx.bot.d.aio_session.get(
    #         f"https://store.steampowered.com/api/appdetails?appids={_id}",
    #         timeout=5
    #     )).json())

    #     if not app_dets[resp[int(_id)]]['success']:
    #         await ctx.respond("No matches found")
    #         return
    #     else:
    #         await ctx.respond(f"{app_dets[resp[int(_id)]]}")
    # except Exception as e:
    #     await ctx.respond(e)

    # await ctx.respond(f"https://store.steampowered.com/app/{resp[name]}")


async def _fetch_trait_map(user: str) -> str:
    """Search if there's a trait map for a query"""
    db = al_listener.bot.d.con
    cursor = db.cursor()
    cursor.execute("SELECT trait FROM traitmap WHERE user=?", (user,))
    return cursor.fetchone()


async def _search_novel(ctx: lb.Context, novel: str):
    """Search a novel on AL"""
    query = """
query ($id: Int, $search: String, $type: MediaType) { 
  Media (id: $id, search: $search, type: $type, sort: POPULARITY_DESC, format_in: [NOVEL]) {
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
    volumes
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

    variables = {"search": novel, "type": "MANGA"}

    response = await ctx.bot.d.aio_session.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": variables},
        timeout=3,
    )

    if not response.ok:
        await ctx.respond(f"Failed to fetch data 😵, error `code: {response.status}`")
        return
    response = (await response.json())["data"]["Media"]

    if not response:
        await ctx.respond("No novel found")

    title = response["title"]["english"] or response["title"]["romaji"]

    no_of_items = response("volumes", "NA")

    if response["description"]:
        response["description"] = parse_description(response["description"])

    else:
        response["description"] = "NA"

    view = views.AuthorView(user_id=ctx.author.id)
    view.add_item(btns.KillButton())
    choice = await ctx.respond(
        embed=hk.Embed(
            title=title,
            url=response["siteUrl"],
            description="\n\n",
            color=colors.ANILIST,
            timestamp=datetime.now().astimezone(),
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
        .set_footer(
            text="Source: AniList",
            icon="https://anilist.co/img/icons/android-chrome-512x512.png",
        ),
        components=view,
    )

    await view.start(choice)
    await view.wait()

    # if hasattr(view, "answer"):  # Check if there is an answer
    #     pass
    # else:
    #     await ctx.edit_last_response(components=[])


async def _search_anime(ctx, anime: str):
    """Search an anime on AL"""
    query = """
query ($id: Int, $search: String, $type: MediaType) { 
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
    studios (isMain: true) {
        nodes {
            name
            siteUrl
        }
    }
    bannerImage
    genres
    status
    description (asHtml: false)
    siteUrl
    nextAiringEpisode {
        episode
    }
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
        await ctx.respond(f"Failed to fetch data 😵, error `code: {response.status}`")
        return

    view = views.AuthorView(user_id=ctx.author.id)
    if not len((await response.json())["data"]["Page"]["media"]) == 1:
        embed = hk.Embed(
            title="Choose the desired anime",
            color=0x43408A,
            timestamp=datetime.now().astimezone(),
        )

        for count, item in enumerate((await response.json())["data"]["Page"]["media"]):
            embed.add_field(
                count + 1, item["title"]["english"] or item["title"]["romaji"]
            )
            view.add_item(
                btns.GenericButton(style=hk.ButtonStyle.PRIMARY, label=f"{count+1}")
            )

        embed.set_image("https://i.imgur.com/FCxEHRN.png")

        choice = await ctx.respond(embed=embed, components=view)

        await view.start(choice)
        await view.wait()

        if hasattr(view, "answer"):  # Check if there is an answer
            num = f"{view.answer}"

        else:
            await ctx.edit_last_response(components=[])
            return

        num = int(num) - 1

    else:
        await ctx.respond(
            hk.Embed(
                description=f"Loading {emotes.LOADING.value}",
                color=colors.ELECTRIC_BLUE,
            )
        )
        num = 0

    response = (await response.json())["data"]["Page"]["media"][num]

    title = response["title"]["english"] or response["title"]["romaji"]

    no_of_items = response["episodes"] if response["episodes"] else "NA"

    if isinstance(response["episodes"], int) and no_of_items == 1:
        no_of_items = (
            verbose_timedelta(timedelta(minutes=response["duration"]))
            if response["duration"]
            else "NA"
        )
    elif response["nextAiringEpisode"]:
        if no_of_items == "NA":
            no_of_items = f"{response['nextAiringEpisode']['episode']}/??"
        else:
            no_of_items = f"{response['nextAiringEpisode']['episode']}/{no_of_items}"

    if response["description"]:
        response["description"] = parse_description(response["description"])

    else:
        response["description"] = "NA"

    try:
        trailer = "Couldn't find anything."

        if response["studios"]["nodes"]:
            studios = ", ".join([st["name"] for st in response["studios"]["nodes"]])
        else:
            studios = "Unknown"

        embed = (
            hk.Embed(
                title=title,
                url=response["siteUrl"],
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field(
                "Rating", response["meanScore"] if response["meanScore"] else "NA"
            )
            .add_field("Genres", ", ".join(response["genres"][:4]))
            .add_field("Status", response["status"].replace("_", " "), inline=True)
            .add_field(
                "Episodes" if response["episodes"] != 1 else "Duration",
                no_of_items,
                inline=True,
            )
            .add_field("Studio", studios, inline=True)
            .add_field("Summary", response["description"])
            .set_thumbnail(response["coverImage"]["large"])
            .set_image(response["bannerImage"])
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        )

        view.clear_items()

        if response["trailer"]:
            if response["trailer"]["site"] == "youtube":
                trailer = f"https://{response['trailer']['site']}.com/watch?v={response['trailer']['id']}"
            else:
                trailer = f"https://{response['trailer']['site']}.com/video/{response['trailer']['id']}"

            view.add_item(
                btns.SwapButton(
                    swap_page=trailer,
                    original_page=embed,
                    label1="Trailer",
                    emoji1=hk.Emoji.parse(emotes.YOUTUBE.value),
                    emoji2=hk.Emoji.parse("🔍"),
                )
            )

        view.add_item(btns.KillButton())
        choice = await ctx.edit_last_response(
            embed=embed,
            components=view,
        )
        await view.start(choice)
        await view.wait()
    except Exception as e:
        print(e)


async def _search_manga(ctx, manga: str):
    """Search a manga on AL and Preview on MD"""
    query = """
query ($id: Int, $search: String, $type: MediaType) {
    Media (id: $id, search: $search, type: $type, 
    sort: POPULARITY_DESC, format_in: [MANGA, ONE_SHOT]) { 
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
    try:
        variables = {"search": manga, "type": "MANGA"}

        response = await ctx.bot.d.aio_session.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
            timeout=3,
        )

        if not response.ok:
            await ctx.respond(
                f"Failed to fetch data 😵, error `code: {response.status}`"
            )
            return

        response = (await response.json())["data"]["Media"]

        if not response:
            await ctx.respond("No manga found")

        title = response["title"]["english"] or response["title"]["romaji"]

        no_of_items = response.get("chapters", response.get("episodes", "NA"))

        if response["description"]:
            response["description"] = parse_description(response["description"])

        else:
            response["description"] = "NA"

        # sess = requests.Session()
        headers = {
            "accept": "application/json",
        }

        search = title
        params = {
            "page": "1",
            "limit": "15",
            "showall": "false",
            "q": search,
            "t": "false",
        }

        res = requests.get(
            "https://api.comick.fun/v1.0/search/",
            params=params,
            headers=headers,
            impersonate="chrome",
        )
        if res.ok and len(res.json()):
            chapter_number = res.json()[0]["last_chapter"]

            no_of_items = no_of_items or chapter_number
            hid = res.json()[0]["hid"]

            no_of_items = f"[{no_of_items}](https://comick.io/comic/{hid})"
        # print("Using MD")
        # base_url = "https://api.mangadex.org"

        # order = {
        #     "rating": "desc",
        #     "followedCount": "desc",
        # }

        # final_order_query = {f"order[{key}]": value for key, value in order.items()}

        # # for key, value in order.items():
        # # final_order_query[f"order[{key}]"] = value

        # req = await ctx.bot.d.aio_session.get(
        #     f"{base_url}/manga",
        #     params={**{"title": title}, **final_order_query},
        #     timeout=3,
        # )

        # if req.ok:
        #     try:
        #         manga_id = (await req.json())["data"][0]["id"]

        #         languages = ["en"]

        #         req = await ctx.bot.d.aio_session.get(
        #             f"{base_url}/manga/{manga_id}/aggregate",
        #             params={"translatedLanguage[]": languages},
        #             timeout=3,
        #         )

        #         print(await req.json())
        #         data = await get_imp_info(await req.json())

        #         if no_of_items == "NA":
        #             no_of_items = (
        #                 f"[{data['latest']['chapter'].split('.')[0]}]("
        #                 f"https://cubari.moe/read/mangadex/{manga_id})"
        #             )
        #         else:
        #             no_of_items = (
        #                 f"[{no_of_items}](https://cubari.moe/read/mangadex/{manga_id})"
        #             )

        #     except IndexError:
        #         data = None
        #         no_of_items = "NA"

        #     except AttributeError:
        #         data = None
        #         no_of_items = "NA"

        # else:
        #     data = None
        #     no_of_items = "NA"

        pages = [
            hk.Embed(
                title=title,
                url=response["siteUrl"],
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Rating", response.get("meanScore", "NA"))
            .add_field("Genres", ", ".join(response.get("genres", [])[:4]) or "NA")
            .add_field("Status", response.get("status", "NA"), inline=True)
            .add_field(
                "Chapters",
                no_of_items or "NA",
                inline=True,
            )
            .add_field("Summary", response.get("description", "NA"))
            .set_thumbnail(response["coverImage"]["large"])
            .set_image(response["bannerImage"])
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        ]

        buttons = [btns.PreviewButton(), btns.KillNavButton()]

        navigator = views.PreView(
            session=ctx.bot.d.aio_session,
            pages=pages,
            buttons=buttons,
            timeout=300,
            user_id=ctx.author.id,
        )

        if isinstance(ctx, lb.SlashContext):
            await navigator.send(ctx.interaction, responded=True)
        else:
            await navigator.send(
                ctx.channel_id,
            )

        # if data:
        #     ctx.bot.d.chapter_info[navigator.message_id] = [
        #         base_url,
        #         data["first"]["id"],
        #         title,
        #         manga_id,
        #         response["coverImage"]["large"],
        #         pages,
        #     ]
        # else:
        #     ctx.bot.d.chapter_info[navigator.message_id] = None

    except Exception as e:
        await ctx.respond(e)


async def _search_characters(ctx: lb.Context, query: str):
    """Interlude function for character search"""

    query = query.split(",")
    if len(query) == 1 or query[1].strip() == "":
        if query[0] in ["birth", "birthday", "bday"]:
            try:
                await ctx.respond(
                    embed=(
                        await (
                            await ALCharacter.is_birthday(ctx.bot.d.aio_session)
                        ).make_embed()
                    )
                )
            except Exception as e:
                await ctx.respond(e)
        else:
            # await ALCharacter.from_search(query[0], ctx.bot.d.aio_session)

            pages = await (
                await ALCharacter.from_search(query[0], ctx.bot.d.aio_session)
            ).make_pages()

            if len(pages) == 1:
                await ctx.respond(embeds=pages)
                return

            view = views.AuthorView(user_id=ctx.author.id)
            view.add_item(
                btns.SwapButton(
                    emoji1=hk.Emoji.parse("<:next:1136984292921200650>"),
                    emoji2=hk.Emoji.parse("<:previous:1136984315415236648>"),
                    original_page=pages[0],
                    swap_page=pages[1],
                )
            )
            view.add_item(btns.KillButton())

            choice = await ctx.respond(
                embed=pages[0],
                components=view,
            )
            await view.start(choice)
            await view.wait()

            # if hasattr(view, "answer"):
            #     pass
            # else:
            #     await ctx.edit_last_response(components=[])

            # await _search_character(ctx, character=query[0])
        return

    else:
        # Make a character picker dropdown from the series
        query_ = """
query ($id: Int, $search: String) { # Define which variables will be used in the query (id)
    Media (id: $id, search: $search) { 
        title {
            english
            romaji
        }
        characters {
            nodes {
                id
                name {
                    full
                    alternative
                }
            }
        }        
    }
    }
  
"""
        try:
            variables = {"search": query[1]}

            response = await ctx.bot.d.aio_session.post(
                "https://graphql.anilist.co",
                json={"query": query_, "variables": variables},
                timeout=3,
            )

            if not response.ok:
                await ctx.respond(
                    f"Failed to fetch data 😵, error `code: {response.status}`"
                )
                return

            response = await response.json()

            view = views.AuthorView(
                user_id=ctx.author.id, session=ctx.bot.d.aio_session
            )

            if query[0].strip() == "":
                options = []
                title = (
                    response["data"]["Media"]["title"]["english"]
                    or response["data"]["Media"]["title"]["romaji"]
                )

                for chara in response["data"]["Media"]["characters"]["nodes"]:
                    options.append(
                        miru.SelectOption(
                            label=chara["name"]["full"], value=chara["id"]
                        )
                    )

                view.add_item(
                    CharacterSelect(
                        options=options, placeholder=f"Select {title} character"
                    )
                )
                view.add_item(btns.KillButton())
                resp = await ctx.respond(content=None, components=view)
                await view.start(resp)
                await view.wait()

            else:
                # chara_choices = {}

                # chara_choices = {
                #     chara["name"]["full"]: chara["id"]
                #     for chara in response["data"]["Media"]["characters"]["nodes"]
                # }

                chara_choices = collections.defaultdict(list)

                for chara in response["data"]["Media"]["characters"]["nodes"]:
                    chara_choices[chara["name"]["full"]] = chara["id"]
                    for name in chara["name"]["alternative"]:
                        chara_choices[name] = chara["id"]

                closest_match, *_ = process.extractOne(
                    query[0],
                    chara_choices.keys(),
                    processor=default_process,
                    scorer=partial_ratio,
                )

                pages = await (
                    await ALCharacter.from_id(
                        chara_choices[closest_match], ctx.bot.d.aio_session
                    )
                ).make_pages()

                if len(pages) == 1:
                    await ctx.respond(embeds=pages)
                    return

                view = views.AuthorView(user_id=ctx.author.id)
                view.add_item(
                    btns.SwapButton(
                        emoji1=hk.Emoji.parse("<:next:1136984292921200650>"),
                        emoji2=hk.Emoji.parse("<:previous:1136984315415236648>"),
                        original_page=pages[0],
                        swap_page=pages[1],
                    )
                )
                view.add_item(btns.KillButton())

                choice = await ctx.respond(
                    embed=pages[0],
                    components=view,
                )
                await view.start(choice)
                await view.wait()

                # if hasattr(view, "answer"):
                #     pass
                # else:
                #     await ctx.edit_last_response(components=[])

                # await ctx.respond(embeds=[await chara.makepages()])

                # await _search_character(ctx, id_=chara_choices[closest_match[0]])

        except Exception as e:
            await ctx.respond(f"Error {e}")


async def _search_vn(ctx: lb.Context, query: str):
    """Search a vn"""
    try:
        url = "https://api.vndb.org/kana/vn"
        headers = {"Content-Type": "application/json"}
        data = {
            "filters": ["search", "=", query],
            "fields": (
                "title, image.url, rating, released, length_minutes, length,"
                "description, tags.spoiler, tags.name,"
                "tags.category, tags.rating,"
                "screenshots.url, screenshots.sexual, screenshots.violence"
            ),
            # "sort": "title"
        }
        # try:
        req = await ctx.bot.d.aio_session.post(
            url, headers=headers, json=data, timeout=3
        )

        if not req.ok:
            await ctx.respond(
                hk.Embed(
                    title="SEARCH ERROR",
                    color=colors.WARN,
                    description=f"Your search query raised a `code:{req.status}` error",
                    timestamp=datetime.now().astimezone(),
                )
            )
            # await ctx.respond("Couldn't find the VN you asked for.")
            return

        req = await req.json()

        if not req["results"]:
            await ctx.respond(
                hk.Embed(
                    title="CAN'T FIND YOUR VN",
                    color=colors.ERROR,
                    description=f"Couldn't find the vn {query}",
                    timestamp=datetime.now().astimezone(),
                ),
                delete_after=15,
            )

        if req["results"][0]["description"]:
            description = parse_vndb_desciption(req["results"][0]["description"])
        else:
            description = "NA"

        if req["results"][0]["released"]:
            date = req["results"][0]["released"].split("-")
            if len(date) == 3:
                released = verbose_date(date[2], date[1], date[0])
            else:
                released = "-".join(date)

        else:
            released = "Unreleased"

        tags = "NA"

        if req["results"][0]["tags"]:
            tags = []
            for tag in sorted(
                req["results"][0]["tags"], key=itemgetter("rating"), reverse=True
            ):
                if tag["category"] == "cont":
                    tags.append(
                        tag["name"] if not tag["spoiler"] else f"||{tag['name']}||"
                    )

                if len(tags) == 7:
                    break

            tags = ", ".join(tags if tags else ["NA"])

        view = views.AuthorView(user_id=ctx.author.id)
        view.add_item(btns.KillButton())

        if req["results"][0]["length_minutes"]:
            hour, mins = divmod(req["results"][0]["length_minutes"], 60)
            time = f"{hour} hours, {mins} minutes" if mins else f"{hour} hours"
        else:
            len_map = {
                1: "Very Short (<2 hours)",
                2: "Short (2-10 hours)",
                3: "Medium (10-30 hours)",
                4: "Long (30-50 hours)",
                5: "Very Long (>50 hours)",
            }
            time = len_map.get(req["results"][0]["length_minutes"], "NA")

        main_embed = (
            hk.Embed(
                title=req["results"][0]["title"],
                url=f"https://vndb.org/{req['results'][0]['id']}",
                color=colors.VNDB,
                timestamp=datetime.now().astimezone(),
            )
            .add_field(
                "Rating",
                req["results"][0]["rating"] or "NA",
            )
            .add_field("Tags", tags)
            .add_field("Released", released, inline=True)
            .add_field("Est. Time", time, inline=True)
            .add_field("Summary", description)
            .set_thumbnail(req["results"][0]["image"]["url"])
            .set_footer(text="Source: VNDB", icon="https://s.vndb.org/s/angel-bg.jpg")
            # components=view,
        )

        screenshots = "\n".join(
            ss["url"]
            for ss in req["results"][0]["screenshots"][:4]
            if not (ss["sexual"] == 2 or ss["violence"] == 2)
        )

        view = views.AuthorView(user_id=ctx.author.id)
        view.add_item(
            btns.SwapButton(
                swap_page=screenshots,
                original_page=main_embed,
                label1="Screenshots",
                emoji1=hk.Emoji.parse("📸"),
                emoji2=hk.Emoji.parse("🔍"),
            )
        )

        view.add_item(btns.KillButton())
        choice = await ctx.respond(
            embed=main_embed,
            components=view,
        )
        await view.start(choice)
        await view.wait()

    except Exception as e:
        await ctx.respond(e)

    # if hasattr(view, "answer"):  # Check if there is an answer
    #     pass
    # else:
    #     await ctx.edit_last_response(components=[])


def replace_bbcode_with_markdown(match: re.Match) -> str:
    """Make a MD string from a re Match object"""
    url = match.group(1)

    # Replacing VNDB ids with the corresponding url
    if url.startswith("/"):
        url = "https://vndb.org" + url

    link_text = match.group(2)
    markdown_link = f"[{link_text}]({url})"
    return markdown_link


def parse_vndb_desciption(description: str) -> str:
    """Parse a VNDB description into a Discord friendly Markdown"""
    description = (
        description.replace("[spoiler]", "||")
        .replace("[/spoiler]", "||")
        .replace("#", "")
        .replace("[i]", "")
        .replace("[b]", "")
        .replace("[/b]", "")
        .replace("[/i]", "")
    )

    pattern = r"\[url=(.*?)\](.*?)\[/url\]"

    # Replace BBCode links with Markdown links in the text
    description = re.sub(pattern, replace_bbcode_with_markdown, description)

    if len(description) > 300:
        description = description[0:300]

        if description.count("||") % 2:
            description = description + "||"

        description = description + "..."

    return description


async def _search_vnchara(ctx: lb.Context, query: str):
    """Search a vn character"""
    url = "https://api.vndb.org/kana/character"
    headers = {"Content-Type": "application/json"}
    data = {
        "filters": ["search", "=", query],
        "fields": "name, description, age, sex,  image.url, traits.name, traits.group_name, vns.title, birthday",
    }

    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data, timeout=3)

    if not req.ok:
        await ctx.respond("Couldn't find the character you asked for.")
        return

    req = await req.json()

    if not req["results"]:
        await ctx.respond(
            hk.Embed(
                title="CAN'T FIND YOUR CHARACTER",
                color=colors.ERROR,
                description=f"Couldn't find the character {query}",
                timestamp=datetime.now().astimezone(),
            ),
            delete_after=15,
        )

    try:
        pages = collections.defaultdict(list)
        options = []
        for i, chara in enumerate(req["results"][:15]):
            if chara["description"]:
                description = parse_vndb_desciption(chara["description"])
            else:
                description = "NA"

            if chara["traits"]:
                traits = {}
                trait_groups = ["Hair", "Eyes", "Body", "Personality"]
                traits = {
                    group: [
                        trait["name"]
                        for trait in chara["traits"]
                        if trait["group_name"] == group
                    ]
                    for group in trait_groups
                }

                traits_string = ""
                for group, names in traits.items():
                    if names:
                        traits_string += f"_{group}_: {', '.join(names[:5])}\n"

                traits = traits_string
            else:
                traits = "NA"

            sex_symbols = {"m": "(♂)", "f": "(♀)", "b": "(⚥)", "n": "(⚲)"}
            if chara["birthday"]:
                birthday = f'{chara["birthday"][1]}/{chara["birthday"][0]}'
            else:
                birthday = "NA"

            embed = [
                hk.Embed(
                    title=f'{chara["name"]} {sex_symbols.get(chara["sex"][0])}',
                    url=f"https://vndb.org/{chara['id']}",
                    color=colors.VNDB,
                    timestamp=datetime.now().astimezone(),
                )
                .add_field("Birthday", birthday, inline=True)
                .add_field("Age", chara["age"] or "NA", inline=True)
                .add_field("Traits", traits)
                .add_field("Summary", description)
                .set_thumbnail(chara["image"]["url"])
                .set_footer(
                    text="Source: VNDB", icon="https://files.catbox.moe/3gg4nn.jpg"
                ),
            ]

            if not i:
                first_page = embed[0]

            options.append(
                miru.SelectOption(
                    label=chara["name"],
                    value=chara["name"],
                    description=chara["vns"][0]["title"],
                )
            )
            pages[chara["name"]] = embed[0]

        view = views.SelectView(user_id=ctx.author.id, pages=pages)
        view.add_item(SimpleTextSelect(options=options, placeholder="Other characters"))
        view.add_item(btns.KillButton())

        resp = await ctx.respond(content=None, embed=first_page, components=view)
        await view.start(resp)
        await view.wait()

    except hk.BadRequestError:
        view = views.AuthorView(user_id=ctx.author.id)
        view.add_item(btns.KillButton())
        resp = await ctx.respond(embed=first_page, components=view)
        await view.start(resp)
        await view.wait()


async def _search_vntag(ctx: lb.Context, query: str):
    """Search a vn tag"""
    url = "https://api.vndb.org/kana/tag"
    headers = {"Content-Type": "application/json"}
    data = {
        "filters": ["search", "=", query],
        "fields": "name, aliases, description, category, vn_count",
        # "sort": "title"
    }
    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data, timeout=3)

    if not req.ok:
        await ctx.respond("Couldn't find the tag you asked for.")
        return

    req = await req.json()

    if not req["results"]:
        await ctx.respond(
            hk.Embed(
                title="CAN'T FIND YOUR TAG",
                color=colors.ERROR,
                description=f"Couldn't find the tag {query}",
                timestamp=datetime.now().astimezone(),
            ),
            delete_after=15,
        )

    if req["results"][0]["description"]:
        description = parse_vndb_desciption(req["results"][0]["description"])
    else:
        description = "NA"

    tag_aliases = ", ".join(req["results"][0].get("aliases", ["NA"]))

    req["results"][0]["category"] = (
        req["results"][0]["category"]
        .replace("cont", "Content")
        .replace("ero", "Sexual")
        .replace("tech", "Technical")
    )

    view = views.AuthorView(user_id=ctx.author.id)
    view.add_item(btns.KillButton())
    choice = await ctx.respond(
        hk.Embed(
            title=req["results"][0]["name"],
            url=f"https://vndb.org/{req['results'][0]['id']}",
            color=colors.VNDB,
            timestamp=datetime.now().astimezone(),
        )
        .add_field("Aliases", tag_aliases)
        .add_field("Category", req["results"][0]["category"], inline=True)
        .add_field("No of VNs", req["results"][0]["vn_count"], inline=True)
        .add_field("Summary", description)
        .set_footer(text="Source: VNDB", icon="https://files.catbox.moe/3gg4nn.jpg"),
        components=view,
    )
    await view.start(choice)
    await view.wait()

    # if hasattr(view, "answer"):  # Check if there is an answer
    #     pass
    # else:
    #     await ctx.edit_last_response(components=[])


async def _search_vntrait(ctx: lb.Context, query: str):
    """Search a vn character trait"""
    url = "https://api.vndb.org/kana/trait"
    headers = {"Content-Type": "application/json"}

    if ctx.guild_id == 695200821910044783:
        db_check = await _fetch_trait_map(query.lower())

        if db_check is not None:
            query = db_check[0]

    data = {
        "filters": ["search", "=", query],
        "fields": "name, aliases, description, group_name, char_count",
        # "sort": "title"
    }

    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data, timeout=3)

    if not req.ok:
        await ctx.respond("Couldn't find the trait you asked for.")
        return

    req = await req.json()

    if not req["results"]:
        await ctx.respond(
            hk.Embed(
                title="CAN'T FIND YOUR TRAIT",
                color=colors.ERROR,
                description=f"Couldn't find the trait {query}",
                timestamp=datetime.now().astimezone(),
            ),
            delete_after=15,
        )

    if req["results"][0]["description"]:
        description = parse_vndb_desciption(req["results"][0]["description"])
    else:
        description = "NA"

    tags = ", ".join(req["results"][0]["aliases"][:5]) or "NA"

    view = views.AuthorView(user_id=ctx.author.id)
    view.add_item(btns.KillButton())
    choice = await ctx.respond(
        hk.Embed(
            title=req["results"][0]["name"],
            url=f"https://vndb.org/{req['results'][0]['id']}",
            color=colors.VNDB,
            timestamp=datetime.now().astimezone(),
        )
        .add_field("Aliases", tags)
        .add_field("Group Name", req["results"][0]["group_name"], inline=True)
        .add_field("No of Characters", req["results"][0]["char_count"], inline=True)
        .add_field("Summary", description)
        .set_footer(text="Source: VNDB", icon="https://files.catbox.moe/3gg4nn.jpg"),
        components=view,
    )
    await view.start(choice)
    await view.wait()

    # if hasattr(view, "answer"):  # Check if there is an answer
    #     pass
    # else:
    #     await ctx.edit_last_response(components=[])


@al_listener.listener(hk.StartedEvent)
async def on_starting(event: hk.StartedEvent) -> None:
    """Event fired on start of bot"""

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


@al_listener.listener(hk.GuildReactionAddEvent)
async def al_link_finder(event: hk.GuildReactionAddEvent) -> None:
    """Check if a message contains an animanga link and display it's info"""

    message = await al_listener.bot.rest.fetch_message(
        event.channel_id, event.message_id
    )

    if not (event.is_for_emoji("🔍") or event.is_for_emoji("🔎")) or message.content:
        return
    list_of_series = anilist_pattern.findall(message.content) or []

    if len(list_of_series) != 0:
        for series in list_of_series:
            query = """
query ($id: Int, $search: String, $type: MediaType) { )
  Media (id: $id, search: $search, type: $type, sort: POPULARITY_DESC) { 
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
                return

            response = (await response.json())["data"]["Media"]

            title = response["title"]["english"] or response["title"]["romaji"]

            no_of_items = response["chapters"] or response["episodes"] or "NA"

            await event.member.send(
                content=(
                    "Here are the details for the series"
                    f"requested here: {message.make_link(message.guild_id)}"
                ),
                embed=hk.Embed(
                    description="\n\n",
                    color=colors.ANILIST,
                    timestamp=datetime.now().astimezone(),
                )
                .add_field("Rating", response["averageScore"])
                .add_field("Genres", ",".join(response["genres"]))
                .add_field("Status", response["status"], inline=True)
                .add_field(
                    "Chapters" if response["type"] == "MANGA" else "ANIME",
                    no_of_items,
                    inline=True,
                )
                .add_field("Summary", parse_description(response["description"]))
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
