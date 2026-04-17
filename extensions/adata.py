"""The animanga related plugin"""

from io import BytesIO
import re
from datetime import datetime, timedelta
from typing import Optional

import hikari as hk
import lightbulb as lb
import miru
from bs4 import BeautifulSoup
from curl_cffi import requests
from rapidfuzz import process
from rapidfuzz.fuzz import partial_ratio
from rapidfuzz.utils import default_process

from utils import buttons as btns
from utils import views as views
from utils.anilist import ALCharacter
from utils.components import CharacterSelect, SimpleTextSelect
from utils.errors import RequestsFailedError
from utils.models import ColorPalette as colors
from utils.models import EmoteCollection as emotes
from utils.misc import verbose_timedelta

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


def parse_description(description: str, limit=400) -> str:
    """Parse Anilist descriptions into Discord friendly markdown

    Args:
        description (str): The description to parse

    Returns:
        str: The parsed description
    """

    if not description or not len(description):
        return "-"

    problematic_tags = ["<i>", "</i>", "<I>", "</I>", "<b>", "</b>", "<B>", "</B>", "<br>", "<BR>", "#"]
    for tag in problematic_tags:
        description = description.replace(tag, "")

    # Adding spoiler tags
    description = description.replace("~!", "||").replace("!~", "||")

    if len(description) > limit:
        description = description[0:limit]

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
@lb.command(
    "lookup",
    "Find something on Anilist or VNDB",
    auto_defer=True,
)
@lb.implements(lb.SlashCommandGroup)
async def al_search(ctx: lb.Context) -> None:
    """A wrapper slash command for AL/VNDB search"""

    pass


@al_search.child
@lb.option(
    "anime",
    "The anime to search for",
)
@lb.command("anime", "Search for an anime on Anilist", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def anime_search(ctx: lb.Context, anime: str) -> None:
    """Search for an anime on AL"""
    return await _search_anime(ctx, anime)

@al_search.child
@lb.option(
    "manga",
    "The manga to search for",
    # autocomplete=True
)
@lb.command("manga", "Search for a manga on Anilist and MangaPark", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def manga_search(ctx: lb.Context, manga: str) -> None:
    """Search for a manga on AL"""
    return await _search_manga(ctx, manga)

@al_search.child
@lb.option(
    "novel",
    "The novel to search for",
    # autocomplete=True
)
@lb.command("novel", "Search for a novel on Anilist", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def novel_search(ctx: lb.Context, novel: str) -> None:
    """Search for a novel on AL"""
    return await _search_novel(ctx, novel)

@al_search.child
@lb.option(
    "character",
    "The character to search for",
    # autocomplete=True
)
@lb.command("character", "Search for an animanga character", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def character_search(ctx: lb.Context, character: str) -> None:
    """Search for a character on AL"""
    return await _search_characters(ctx, character)


@al_search.child
@lb.option(
    "game",
    "The game to search for"
)
@lb.command("game", "Search for a game on Steam", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def game_search(ctx: lb.Context, game: str) -> None:
    """Search for a game on Steam"""
    return await _search_game(ctx, game)


# ============= LOOKUP SLASH COMMANDS END HERE =============

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

    query = """
query Query($name: String) {
  User(name: $name) {
    id
    name
    about
    avatar {
      medium
    }
  }
}
"""

    variables = {"name": user}

    response = await ctx.bot.d.aio_session.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": variables},
    )

    if not response.ok:
        return await ctx.respond(f"https://anilist.co/user/{user}")

    resp = (await response.json())["data"]["User"]



    await ctx.respond(
        content=f"https://anilist.co/user/{resp['id']}",
        embed=hk.Embed(
            title=f"{resp['name']}",
            url=f"https://anilist.co/user/{resp['name']}",
            description=f"{resp['name']}'s Anilist profile",
            color=colors.ANILIST,
            timestamp=datetime.now().astimezone(),
        ).set_image(f"https://img.anili.st/user/{resp['id']}"),
    )


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

    if query in ['bday', 'birthday', 'birth']:
        return await _search_characters(ctx, query, birthday=True)

    query = query.split(',')
    if len(query) > 1:
        series = query[-1]
        query = ",".join(query[:-1])
        return await _search_characters(ctx, query, series)

    await _search_characters(ctx, query[0])

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
            data = await (await ctx.bot.d.aio_session.get(url)).json()
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
        "https://api.jikan.moe/v4/top/anime", params=params
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
@lb.add_checks(lb.dm_only | lb.nsfw_channel_only)
@lb.option("code", "You know it", int)
@lb.command("nh", "Search 🌚", pass_options=True, hidden=True)
@lb.implements(lb.PrefixCommand)
async def nhhh(ctx: lb.PrefixContext, code: int):
    """Not gonna elaborate this one"""

    res = await ctx.bot.d.aio_session.get(
        f"https://cubari.moe/read/api/nhentai/series/{code}/",
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

        navigator = views.AuthorNavi(
            pages=pages, timeout=1800, user_id=ctx.author.id, buttons="default"
        )
        await navigator.send(ctx.channel_id)

    else:
        await ctx.respond("Didn't work")
        print(res.json())


@al_listener.command
@lb.option(
    "query", "The voice actor to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("voiceactor", "Search a voice actor on AniList", pass_options=True, aliases=["seiyuu", "va"])
@lb.implements(lb.PrefixCommand)
async def voiceactor_search(ctx: lb.PrefixContext, query: str):
    """Search for a voice actor on AniList
    
    Args:
        ctx (lb.PrefixContext): The context
        query (str): The voice actor to search for
    """
    return await _search_voiceactor(ctx, query)


@al_listener.command
@lb.option(
    "query", "The studio to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("studio", "Search a studio on AniList", pass_options=True, aliases=["st"])
@lb.implements(lb.PrefixCommand)
async def studio_search(ctx: lb.PrefixContext, query: str):
    """Search for a studio on AniList"""
    return await _search_studio(ctx, query)
    
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
    
    return await _search_game(ctx, query)


async def _search_game(ctx: lb.Context, query: str):
    session = requests.Session(impersonate="chrome")

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

    r = session.get(
        "https://store.steampowered.com/search/suggest", params=params, timeout=5
    )

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

    soup = BeautifulSoup(r.content, "lxml")

    sup = soup.find("a")

    if not sup:
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
    sup = sup.get("href")

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


async def _search_studio(ctx: lb.Context, query: str):

    json_data = {
        'query': 'query Query($search: String, $sort: [MediaSort]) {\r\n  Studio(search: $search) {\r\n    name\r\n    siteUrl\r\n    id\r\n    favourites\r\n    media(sort: $sort) {\r\n      nodes {\r\n        title {\r\n          english\r\n          romaji\r\n        }\r\n        coverImage {\r\n          large\r\n        }\r\n        averageScore\r\n      }\r\n    }\r\n  }\r\n}',
        'variables': {
            'search': query,
            'sort': 'FAVOURITES_DESC',
        },
    }

    response = await ctx.bot.d.aio_session.post('https://graphql.anilist.co', json=json_data)
    
    if not response.ok:
        await ctx.respond(f"Failed to fetch data 😵, error `code: {response.status}`")
        return
    response = (await response.json())["data"]["Studio"]
    
    desc = ""
    
    for media in response['media']['nodes']:
        desc += f"{media['title']['english'] or media['title']['romaji']} - {media['averageScore']}\n"
    
    
    await ctx.respond(
        hk.Embed(
            title=response['name'],
            url=response['siteUrl'],
            color=colors.ANILIST,
            timestamp=datetime.now().astimezone(),
        )
        .add_field("Favourites", response['favourites'])
        # .add_field("Media", len(response['media']['nodes']))
        .add_field("Description", desc)
        .set_footer(
            text="Source: AniList",
            icon="https://anilist.co/img/icons/android-chrome-512x512.png",
        )
    )


def _parse_non_anime_roles(description: str) -> list:
    """Parse non-anime roles from staff description"""
    if not description:
        return []
    
    non_anime_roles = []
    
    def parse_role(possible_role):
        return possible_role.strip().lstrip(':').lstrip('*').lstrip('•').lstrip('-').strip()
    
    for section in description.split('\n\n'):
        if 'nonanimeroles' in section.lower().replace('-', '').replace('_', '').replace(' ', ''):
            for possible_role in section.split("\n"):
                if 'tv series' in possible_role.lower() or 'role' in possible_role.lower():
                    continue
                
                if 'vg' in possible_role.lower() or 'game' in possible_role.lower():
                    possible_role = parse_role(possible_role)
                    possible_role = re.sub(r"\s*\((VG|Video Game)\)\s*", "", possible_role, flags=re.IGNORECASE)
                    
                    match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", possible_role.strip())
                    if match:
                        character_name = match.group(1).strip()
                        possible_role = possible_role.replace(f"[{character_name}]({match.group(2)})", "").strip()
                    else:
                        character_name = possible_role.split('-')[0].strip()
                        possible_role = possible_role.replace(character_name, "").strip()
                    
                    series = parse_role(possible_role)
                    if character_name and series:
                        non_anime_roles.append({
                            'character': character_name,
                            'series': series,
                            'type': 'game',
                        })
                else:
                    match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", possible_role.strip())
                    if match:
                        character_name = match.group(1).strip()
                        possible_role = possible_role.replace(f"[{character_name}]({match.group(2)})", "").strip()
                    else:
                        character_name = possible_role.split('(')[0].strip()
                        possible_role = possible_role.replace(character_name, "").strip()
                    
                    series = parse_role(possible_role)
                    if series and series.startswith('(') and series.endswith(')'):
                        series = series[1:-1]
                    
                    if character_name and series:
                        non_anime_roles.append({
                            'character': parse_role(character_name),
                            'series': series,
                            'type': 'other',
                        })
    
    return non_anime_roles

from utils.card import card_maker



def trim_va_description(description: str) -> str:
    """Specific logic to trim the description for voice actors"""
    
    paragraphs = []
    
    skip_terms = ['height', 'agency', 'twitter', 'awards', 'instagram', 'website', 'anime roles']
    
    for paragraph in description.split('\n\n'):
        if any(term in paragraph.lower() for term in skip_terms):
            continue
        paragraphs.append(paragraph)
    
    return '\n\n'.join(paragraphs)



async def _search_voiceactor(ctx: lb.Context, query: str):
    """Search for a voice actor on AniList"""
    query_str = """
query Staff($search: String, $sort: [MediaSort], $charactersSort: [CharacterSort], $perPage: Int) {
  Staff(search: $search) {
    dateOfBirth {
      year
      month
      day
    }
    age
    gender
    favourites
    description
    image {
      medium
    }
    name {
      full
    }
    yearsActive
    siteUrl
    characters(sort: $charactersSort, perPage: $perPage) {
      nodes {
        favourites
        name {
          full
        }
        image {
          medium
        }
        media(sort: $sort) {
          nodes {
            title {
              english
              romaji
            }
            type
            favourites
          }
        }
      }
    }
  }
}
"""
    try:
        json_data = {
            'query': query_str,
            'variables': {
                'search': query,
                'sort': 'FAVOURITES_DESC',
                'charactersSort': 'FAVOURITES_DESC',
                'perPage': 10,
            },
        }
        
        response = await ctx.bot.d.aio_session.post('https://graphql.anilist.co', json=json_data)
        
        if not response.ok:
            await ctx.respond(
                hk.Embed(
                    title="ERROR FETCHING DATA",
                    color=colors.ERROR,
                    description=f"Failed to fetch data 😵, error `code: {response.status}`",
                    timestamp=datetime.now().astimezone(),
                ),
                delete_after=15,
            )
            return
        
        response_data = await response.json()
        
        if not response_data.get('data', {}).get('Staff'):
            await ctx.respond(
                hk.Embed(
                    title="VOICE ACTOR NOT FOUND",
                    color=colors.ERROR,
                    description=f"Couldn't find voice actor `{query}` 😵",
                    timestamp=datetime.now().astimezone(),
                ),
                delete_after=15,
            )
            return
        
        data = response_data['data']['Staff']
        
        # Parse date of birth
        dob = ""
        if data['dateOfBirth']:
            if data['dateOfBirth'].get('day') and data['dateOfBirth'].get('month'):
                dob = f"{data['dateOfBirth']['day']}/{data['dateOfBirth']['month']}"
                # if data['dateOfBirth'].get('year'):
                #     dob += f"/{data['dateOfBirth']['year']}"
        
        # Parse description
        description = parse_description(trim_va_description(data.get('description', '')), limit=300) if data.get('description') else "NA"
        
        # Parse non-anime roles
        non_anime_roles = _parse_non_anime_roles(data.get('description', ''))
        
        # Get anime roles
        anime_roles = []
        
        characters = data.get('characters', {}).get('nodes', [])
        
        if not characters:
            await ctx.respond(
                hk.Embed(
                    title="NO VA ROLES FOUND",
                    color=colors.WARN,
                    description=f"{data.get('name', {}).get('full', '')} has no voice acting roles. Visit {data.get('siteUrl', '')} to view info about them.",
                    timestamp=datetime.now().astimezone(),
                ),
                delete_after=15,
            )
        
        for character in characters:
            
            
            if character.get('media', {}).get('nodes'):
                media = character['media']['nodes'][0]
                anime_roles.append({
                    'title': character['name']['full'],
                    'image': character.get('image', {}).get('medium'),
                    # 'favourites': character.get('favourites', 0),
                    'subtitle': media.get('title', {}).get('english') or media.get('title', {}).get('romaji'),
                })
        
        if anime_roles:
            card_image = card_maker(anime_roles)
            image = BytesIO()
            card_image.save(image, format='PNG')
            image.seek(0)
        else:
            image = BytesIO()

        
        # await ctx.respond(image)
        
        # Build embed
        embed = (
            hk.Embed(
                title=data['name']['full'],
                url=data.get('siteUrl', ''),
                # description=description,
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .set_thumbnail(data.get('image', {}).get('medium'))
            .set_image(hk.Bytes(image, 'va_card.png'))
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        )
        
        # Add basic info fields
        info_fields = []
        # if data.get('gender'):
        #     info_fields.append(("Gender", data['gender'], True))
        # if dob:
        #     info_fields.append(("Date of Birth", dob, True))
        # if data.get('age'):
        #     info_fields.append(("Age", str(data['age']), True))
        if data.get('yearsActive'):
            
            if len(data['yearsActive']) == 1:
                years_active = f"{data['yearsActive'][0]} - Present"
            elif len(data['yearsActive']) == 2:
                years_active = f"{data['yearsActive'][0]} - {data['yearsActive'][1]}"
            else:
                years_active = str(data['yearsActive'])
            info_fields.append(("Years Active", years_active, True))
        if data.get('favourites'):
            info_fields.append(("Favourites", f"{data['favourites']}❤", True))
        
        for name, value, inline in info_fields:
            embed.add_field(name, value, inline=inline)
        
        embed.add_field("Description", description, inline=False)
        
        if non_anime_roles:
            embed.add_field("Other Roles", ",".join([f"{role['character']}"  for role in non_anime_roles[:5]]), inline=False)
        
        # Add top anime roles
        # if anime_roles:
        #     top_roles = sorted(anime_roles, key=lambda x: x.get('favourites', 0), reverse=True)[:5]
        #     roles_text = "\n".join([
        #         f"{role['character']} ({role['series']})"
        #         for role in top_roles
        #     ])
        #     # if len(anime_roles) > 5:
        #     #     roles_text += f"\n*...and {len(anime_roles) - 5} more*"
        #     embed.add_field("Top Anime Roles", roles_text, inline=False)
        
        
        
        # Add non-anime roles if any
        # if non_anime_roles:
        #     non_anime_text = "\n".join([
        #         f"{role['character']} ({role['series']})"
        #         for role in non_anime_roles[:5]
        #     ])
        #     # if len(non_anime_roles) > 5:
        #     #     non_anime_text += f"\n*...and {len(non_anime_roles) - 5} more*"
        #     embed.add_field("Video Game Roles", non_anime_text, inline=False)
        
        await ctx.respond(embed=embed)
        
    except Exception as e:
        await ctx.respond(e)
    

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
    )

    if not response.ok:
        await ctx.respond(f"Failed to fetch data 😵, error `code: {response.status}`")
        return
    response = (await response.json())["data"]["Media"]

    if not response:
        await ctx.respond("No novel found")

    title = (response["title"]["english"] or response["title"]["romaji"])[:99]


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
            response.get("volumes") or "NA",
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
    )

    if not response.ok:
        return await ctx.respond(f"Failed to fetch data 😵, error `code: {response.status}`")
    if not len((await response.json())["data"]["Page"]["media"]):
        return await ctx.respond("Your query doesn't match any results 😵")

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
            no_of_items = f"{response['nextAiringEpisode']['episode']-1}/??"
        else:
            no_of_items = f"{response['nextAiringEpisode']['episode']-1}/{no_of_items}"

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
    Page (perPage: 5) {
        media (id: $id, search: $search, type: $type, 
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
}
"""
    try:
        variables = {"search": manga, "type": "MANGA"}

        response = await ctx.bot.d.aio_session.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
        )

        if not response.ok:
            await ctx.respond(
                f"Failed to fetch data 😵, error `code: {response.status}`"
            )
            return

        options = []
        pages = {}
        
        series_list = (await response.json())["data"]["Page"]["media"]
        if not series_list:
            await ctx.respond("No manga found")
            return
        
        if len(series_list) > 1:
        
            for idx, series in enumerate(series_list):
                options.append(
                    miru.SelectOption(
                        label=(series["title"]["english"] or series["title"]["romaji"])[:99],
                        value=idx,
                        description=series["description"][:75] + "..." if series["description"] else "",
                        )
                    )

            view = views.AuthorView(user_id=ctx.author.id)
            view.add_item(SimpleTextSelect(options=options, placeholder="Select a manga"))
            view.add_item(btns.KillButton())

            resp = await ctx.respond(components=view)
            await view.start(resp)

            await view.wait_for_input(timeout=20)
            
            try:
                response_idx = int(view.children[0].values[0])
            except Exception:
                response_idx = 0
        
        else:
            response_idx = 0
            await ctx.respond(
                hk.Embed(
                    description=f"Loading {emotes.LOADING.value}",
                    color=colors.ELECTRIC_BLUE,
                )
            )


        response = (await response.json())["data"]["Page"]["media"][response_idx]

        if not response:
            await ctx.respond("No manga found")

        title = (response["title"]["english"] or response["title"]["romaji"])[:99]

        no_of_items = response.get("chapters", response.get("episodes", "NA"))

        if response["description"]:
            response["description"] = parse_description(response["description"])
        else:
            response["description"] = "NA"

        cookies = {
            'theme': 'mdark',
            'wd': '959x710',
        }
        MANGAPARK_URL = 'https://mangapark.io'

        headers = {
            'accept': '*/*',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': MANGAPARK_URL,
            'pragma': 'no-cache',
            'referer': f'{MANGAPARK_URL}/',
        }

        json_data = {
            'query': 'query get_searchComic($select: SearchComic_Select) {\n    get_searchComic(\n      select: $select\n    ) {\n      reqPage reqSize reqSort reqWord\n      newPage\n      paging { \n  total pages page init size skip limit prev next\n }\n      items {\n        id data {\n          id dbStatus name\n          origLang tranLang\n          urlPath urlCover600 urlCoverOri\n          genres altNames authors artists\n          is_hot is_new sfw_result\n          score_val follows reviews comments_total\n          max_chapterNode {\n            id data {\n              id dateCreate\n              dbStatus isFinal sfw_result\n              dname urlPath is_new\n              userId userNode {\n                id data {\n                  id name uniq avatarUrl urlPath\n                }\n              }\n            }\n          }\n        }\n        sser_follow\n        sser_lastReadChap {\n          date chapterNode {\n            id data {\n              id dbStatus isFinal sfw_result\n              dname urlPath is_new\n              userId userNode {\n                id data {\n                  id name uniq avatarUrl urlPath\n                }\n              }\n            }\n          }\n        }\n      }\n    }\n  }',
            'variables': {
                'select': {
                    'word': title,
                    'size': 10,
                    'page': 1,
                    'sortby': 'field_score',
                },
            },
        }


        # Create initial embed without chapter count
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
                "Loading...",
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

        await ctx.edit_last_response(embeds=pages, components=None)

        # Fetch chapter count in background and update
        try:
            res = requests.post(f'{MANGAPARK_URL}/apo/', cookies=cookies, headers=headers, json=json_data)
            if res and res.ok and len(res.json()['data']['get_searchComic']['items']):
                
                selected_series = res.json()['data']['get_searchComic']['items'][0]
                chapter_number = selected_series['data']['max_chapterNode']['data']['dname']
                chapter_number = re.search(r'Ch\.(\d+)', chapter_number).group(1) if re.search(r'Ch\.(\d+)', chapter_number) else chapter_number
                chapter_number = chapter_number.lower().replace('chapter', '').replace('vol', '').lstrip('0')

                url = f'{MANGAPARK_URL}{selected_series["data"]["urlPath"]}'

                updated_no_of_items = f"[{chapter_number}]({url})" if chapter_number else "NA"
            else:
                updated_no_of_items = "NA"
        except Exception:
            updated_no_of_items = "NA"

        # Update the embed with the fetched chapter count
        updated_pages = [
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
                updated_no_of_items,
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


            
        view = views.AuthorView(user_id=ctx.author.id)
        view.add_item(btns.KillButton())
        
        await ctx.edit_last_response(embeds=updated_pages, components=view)

    except Exception as e:
        await ctx.respond(e)


from utils.algorithms import longest_common_substring

def cleanup_character_description_for_dropdown(description: str) -> str:
    parsed_desc = parse_description(description)
    
    desc_lines = parsed_desc.split('\n')
    
    final_desc = ""
    
    for line in desc_lines:
        
        line = line.strip()
        if line.startswith('**') or line.startswith('__') or line.startswith('||'):
            pass
        else:
            final_desc += line + "\n"
    
    return final_desc.strip()[:50] if final_desc.strip() else "-"
    

async def _search_characters(ctx: lb.Context, query: str, series: Optional[str] = None, birthday: Optional[bool] = False):
    """Interlude function for character search with dropdowns sorted by popularity"""

    if birthday:
        try:
            characters = await ALCharacter.get_birthday_characters(ctx.bot.d.aio_session)
            
            if not characters:
                await ctx.respond("No characters have their birthday today 😵")
                return
            
            # Create dropdown options for birthday characters
            options = []
            for char in characters:
                label = char["name"]["full"]
                if char["favourites"]:
                    label += f" ({char['favourites']}❤)"
                
                
                series_titles = [node["title"]["romaji"] or node["title"]["english"] for node in char["media"]["nodes"]]
                
                options.append(
                    miru.SelectOption(
                        label=label[:100],
                        value=str(char["id"]),
                        description=longest_common_substring(series_titles)
                        # description=cleanup_character_description_for_dropdown(char["description"])
                    )
                )
            
            view = views.AuthorView(
                user_id=ctx.author.id, session=ctx.bot.d.aio_session
            )
            
            view.add_item(
                CharacterSelect(
                    options=options, 
                    placeholder="Select character"
                )
            )
            view.add_item(btns.KillButton())
            
            resp = await ctx.respond(content=f"🎂 {len(characters)} characters have their birthday today:", components=view)
            await view.start(resp)
            await view.wait()
            
        except Exception as e:
            await ctx.respond(f"Error getting birthday characters: {e}")
        return
    
    if not series:
        # General character search - show dropdown with multiple results
        try:
            characters = await ALCharacter.from_search_multiple(query, ctx.bot.d.aio_session, per_page=25)
            
            if not characters:
                await ctx.respond("No characters found for your search query 😵")
                return
            
            # Create dropdown options sorted by popularity (already sorted by API)
            options = []
            for char in characters:
                # Format label with popularity info
                label = char["name"]["full"]
                if char["favourites"]:
                    label += f" ({char['favourites']}❤)"
                
                
                series_titles = [node["title"]["romaji"] or node["title"]["english"] for node in char["media"]["nodes"]]
                
                options.append(
                    miru.SelectOption(
                        label=label[:100],  # Discord limit
                        value=str(char["id"]),
                        description=longest_common_substring(series_titles)
                        # description=cleanup_character_description_for_dropdown(char["description"])
                    )
                )
            
            view = views.AuthorView(
                user_id=ctx.author.id, session=ctx.bot.d.aio_session
            )
            
            view.add_item(
                CharacterSelect(
                    options=options, 
                    placeholder=f"Select character"
                )
            )
            view.add_item(btns.KillButton())
            
            resp = await ctx.respond(content=f"Found {len(characters)} characters for '{query}'", components=view)
            await view.start(resp)
            await view.wait()
            
        except Exception as e:
            await ctx.respond(f"Error searching characters: {e}")
        return

    else:
        # Series-specific character search
        try:
            title, characters = await ALCharacter.from_series_characters(series, ctx.bot.d.aio_session)
            
            if not title or not characters:
                await ctx.respond(f"Couldn't find series '{series}' or no characters found 😵")
                return
            
            if query.strip() == "":
                # Show all characters from the series
                options = []
                for char in characters:
                    label = char["name"]["full"]
                    if char["favourites"]:
                        label += f" ({char['favourites']}❤)"
                    
                    options.append(
                        miru.SelectOption(
                            label=label[:100],
                            value=str(char["id"]),
                            description=cleanup_character_description_for_dropdown(char["description"])
                        )
                    )
                
                view = views.AuthorView(
                    user_id=ctx.author.id, session=ctx.bot.d.aio_session
                )
                
                view.add_item(
                    CharacterSelect(
                        options=options, 
                        placeholder=f"Select {title[:50]} character"
                    )
                )
                view.add_item(btns.KillButton())
                
                resp = await ctx.respond(content=f"Found {len(characters)} characters from '{title[:50]}'", components=view)
                await view.start(resp)
                await view.wait()
                
            else:
                # Search for specific character within the series
                chara_choices = {}
                
                for char in characters:
                    chara_choices[char["name"]["full"]] = char["id"]
                    for name in char["name"]["alternative"]:
                        chara_choices[name] = char["id"]
                
                # Find all characters with similar names (not just the closest match)
                similar_characters = []
                query_lower = query.lower()
                
                for char in characters:
                    char_name = char["name"]["full"].lower()
                    alt_names = [name.lower() for name in char["name"]["alternative"]]
                    
                    # Check if query is contained in the character name or alternative names
                    if (query_lower in char_name or 
                        any(query_lower in alt for alt in alt_names) or
                        any(alt.startswith(query_lower) for alt in alt_names) or
                        char_name.startswith(query_lower)):
                        similar_characters.append(char)
                
                # If no similar characters found, fall back to fuzzy matching
                if not similar_characters:
                    closest_match, score, *_ = process.extractOne(
                        query,
                        chara_choices.keys(),
                        processor=default_process,
                        scorer=partial_ratio,
                    )
                    
                    # Only include if the match is reasonably close (score > 60)
                    if score > 60:
                        char_id = chara_choices[closest_match]
                        char_data = next((c for c in characters if c["id"] == char_id), None)
                        if char_data:
                            similar_characters.append(char_data)
                
                if not similar_characters:
                    await ctx.respond(f"No characters matching '{query}' found in '{title}' 😵")
                    return
                
                # Create dropdown options for similar characters
                options = []
                for char in similar_characters:
                    label = char["name"]["full"]
                    if char["favourites"]:
                        label += f" ({char['favourites']}❤)"
                    
                    options.append(
                        miru.SelectOption(
                            label=label[:100],
                            value=str(char["id"]),
                            description=cleanup_character_description_for_dropdown(char["description"])
                        )
                    )
                
                view = views.AuthorView(
                    user_id=ctx.author.id, session=ctx.bot.d.aio_session
                )
                
                view.add_item(
                    CharacterSelect(
                        options=options, 
                        placeholder=f"Select character from '{title[:50]}'"
                    )
                )
                view.add_item(btns.KillButton())
                
                resp = await ctx.respond(
                    content=f"Found {len(similar_characters)} character(s) matching '{query}' in '{title}':", 
                    components=view
                )
                await view.start(resp)
                await view.wait()

        except Exception as e:
            await ctx.respond(f"Error searching series characters: {e}")



async def _search_movie(ctx: lb.Context, query: str, filter_: Optional[str] = None):
    """Search a movie"""
    headers = {
        'accept': 'application/json',
    }

    params = {
        'query': query,
    }

    response = await ctx.bot.d.aio_session.get('https://api.imdbapi.dev/search/titles', params=params, headers=headers)

    if not response.ok:
        await ctx.respond("Couldn't find the movie you asked for.")
        return

    response = await response.json()
    
    if filter_:
        for movie in response['titles']:
            if movie['type'] == filter_:
                movie_id = movie['id']
                break
        else:
            await ctx.respond("Couldn't find the movie you asked for.")
            return
    else:
        movie_id = response['titles'][0]['id']
    
    movie_data = await ctx.bot.d.aio_session.get(f'https://api.imdbapi.dev/titles/{movie_id}', headers=headers)
    movie_data = await movie_data.json()
    

    await ctx.respond(
        hk.Embed(
            title=f"{movie_data['primaryTitle']} ({movie_data['startYear']})",
            url=f'https://www.imdb.com/title/{movie_id}',
            color=colors.IMDB,
            timestamp=datetime.now().astimezone(),
        )
        .add_field('Rating', f"{movie_data['rating']['aggregateRating']}")
        .add_field('Genres', ", ".join(movie_data.get('genres', [])[:4]) or "-", inline=True)
        .add_field('Runtime', verbose_timedelta(timedelta(seconds=movie_data.get('runtimeSeconds', 0))), inline=True)
        .add_field('Summary', movie_data.get('plot', '-')[:200])
        .set_thumbnail(movie_data['primaryImage']['url'])
        .set_footer(text='Source: IMDB', icon='https://www.imdb.com/favicon.ico')
    )


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
