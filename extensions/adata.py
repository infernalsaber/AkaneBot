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
from utils.anilist import (
    ALAnime,
    ALCharacter,
    ALManga,
    ALNovel,
    ALStaff,
    ALStudio,
    ALUser,
    AnilistBase,
)
from utils.anilist_graph import find_series_name
from utils.components import CharacterSelect, SimpleTextSelect
from utils.errors import RequestsFailedError
from utils.models import ColorPalette as colors
from utils.models import EmoteCollection as emotes
from utils.misc import verbose_timedelta, truncate_words, get_random_quote

al_listener = lb.Plugin(
    "Anilist",
    "Search functions for anime, manga, characters, seiyuu and more",
    include_datastore=True,
)
al_listener.d.help_image = "https://i.imgur.com/2nEsM2W.png"
al_listener.d.help = True
al_listener.d.help_emoji = "🌸"


anilist_pattern = re.compile(
    r"\b(https?:\/\/)?(www.)?anilist.co\/(anime|manga)\/(\d{1,6})"
)


parse_description = AnilistBase.parse_description


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
@lb.command("manga", "Search for a manga on Anilist", pass_options=True, auto_defer=True)
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




# ============= LOOKUP SLASH COMMANDS END HERE =============

@al_listener.command
@lb.add_cooldown(30, 3, lb.GlobalBucket)
@lb.set_max_concurrency(2, lb.GlobalBucket)
@lb.option(
    "series",
    "The series to get the watch order for",
    modifier=lb.commands.OptionModifier.CONSUME_REST,
)
@lb.command(
    "watch-order",
    "Time investment needed by a series and watch order",
    aliases=["timeto", "watchorder", "wo"],
    pass_options=True,
    auto_defer=True,
)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def time_to(ctx: lb.Context, series: str) -> None:
    """Time investment needed by a series and watch order"""
    return await _time_to(ctx, series)

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
    """Search a manga on AL

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

    al_user = await ALUser.from_name(user, ctx.bot.d.anilist)
    if al_user is None:
        return await ctx.respond(f"https://anilist.co/user/{user}")

    await ctx.respond(
        content=f"https://anilist.co/user/{al_user.id}",
        embed=hk.Embed(
            title=al_user.name,
            url=f"https://anilist.co/user/{al_user.name}",
            description=f"{al_user.name}'s Anilist profile",
            color=colors.ANILIST,
            timestamp=datetime.now().astimezone(),
        ).set_image(f"https://img.anili.st/user/{al_user.id}"),
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
@lb.command("voiceactor", "Search a voice actor on AniList", pass_options=True, aliases=["seiyuu", "va"], auto_defer=True)
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
@lb.command("studio", "Search a studio on AniList", pass_options=True, aliases=["st"], auto_defer=True)
@lb.implements(lb.PrefixCommand)
async def studio_search(ctx: lb.PrefixContext, query: str):
    """Search for a studio on AniList"""
    return await _search_studio(ctx, query)
    
@al_listener.command
@lb.add_checks(lb.owner_only)
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
                title="GAME NOT FOUND",
                color=colors.ERROR,
                description=f"Couldn't find game `{query}` 😵",
                timestamp=datetime.now().astimezone(),
            )
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
    """Search for a studio on AniList"""
    await ctx.respond(f"{get_random_quote()} {hk.Emoji.parse(emotes.LOADING.value)}")
    try:
        studio = await ALStudio.from_search(query, ctx.bot.d.anilist)
        if not studio:
            await ctx.edit_last_response(
                content=None,
                embed=hk.Embed(
                    title="STUDIO NOT FOUND",
                    color=colors.ERROR,
                    description=f"Couldn't find studio `{query}` on AniList 😵",
                    timestamp=datetime.now().astimezone(),
                ),
            )
            return

        media_nodes = studio.get('media_nodes') or studio.get('media', {}).get('nodes', [])
        studio_works = []
        seen_anime_ids = set()

        def collect_related_anime_ids(data_obj, visited_set):
            if isinstance(data_obj, dict):
                if data_obj.get("type") == "ANIME" or "title" in data_obj:
                    if "id" in data_obj:
                        visited_set.add(data_obj["id"])
                for v in data_obj.values():
                    collect_related_anime_ids(v, visited_set)
            elif isinstance(data_obj, list):
                for item in data_obj:
                    collect_related_anime_ids(item, visited_set)

        for media in media_nodes:
            media_id = media.get('id')
            if not media_id or media_id in seen_anime_ids:
                continue

            collect_related_anime_ids(media, seen_anime_ids)

            title = media.get('title', {}).get('english') or media.get('title', {}).get('romaji') or "Unknown"
            score = media.get('averageScore')
            cover_image = media.get('coverImage', {}).get('large')

            if cover_image:
                studio_works.append({
                    'title': title,
                    'image': cover_image,
                    'subtitle': f"Score: {score}" if score is not None else "Score: NA",
                })

            if len(studio_works) == 8:
                break

        if studio_works:
            card_image = await card_maker(studio_works, ctx.bot.d.anilist)
            image = BytesIO()
            card_image.save(image, format='PNG')
            image.seek(0)
        else:
            image = BytesIO()

        embed = (
            hk.Embed(
                title=studio['name'],
                url=studio['siteUrl'],
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .set_image(hk.Bytes(image, 'studio_card.png'))
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        )

        if studio.get('favourites') is not None:
            embed.add_field("Favourites", f"{studio['favourites']}❤", inline=True)

        view = views.AuthorView(user_id=ctx.author.id)
        view.add_item(btns.KillButton())

        choice = await ctx.edit_last_response(content=None, embed=embed, components=view)
        await view.start(choice)
        await view.wait()

    except Exception as e:
        await ctx.edit_last_response(f"Error: {e}")


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
                    character_name = parse_role(character_name)
                    if character_name and series and character_name != "~!":
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
                    
                    character_name = parse_role(character_name)
                    if character_name and series and character_name != "~!":
                        non_anime_roles.append({
                            'character': character_name,
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
    await ctx.respond(f"{get_random_quote()} {hk.Emoji.parse(emotes.LOADING.value)}")
    try:
        data = await ALStaff.from_search(query, ctx.bot.d.anilist, per_page=15)

        if not data:
            await ctx.edit_last_response(
                content=None,
                embed=hk.Embed(
                    title="VOICE ACTOR NOT FOUND",
                    color=colors.ERROR,
                    description=f"Couldn't find voice actor `{query}` 😵",
                    timestamp=datetime.now().astimezone(),
                ),
            )
            return
        
        # Parse date of birth
        dob = ""
        if data['dateOfBirth']:
            if data['dateOfBirth'].get('day') and data['dateOfBirth'].get('month'):
                dob = f"{data['dateOfBirth']['day']}/{data['dateOfBirth']['month']}"
        
        # Parse description
        description = parse_description(trim_va_description(data.get('description', '')), limit=300) if data.get('description') else "NA"
        
        # Parse non-anime roles
        non_anime_roles = _parse_non_anime_roles(data.get('description', ''))
        
        # Get anime roles
        anime_roles = []
        
        characters = data.get('characters', {}).get('nodes', [])
        
        if not characters:
            await ctx.edit_last_response(
                content=None,
                embed=hk.Embed(
                    title="NO VA ROLES FOUND",
                    color=colors.WARN,
                    description=f"{data.get('name', {}).get('full', '')} has no voice acting roles. Visit {data.get('siteUrl', '')} to view info about them.",
                    timestamp=datetime.now().astimezone(),
                ),
            )
            return
        
        for character in characters:
            if character.get('image', {}).get('medium') and character.get('media', {}).get('nodes'):
                media = character['media']['nodes'][0]
                subtitle = media.get('title', {}).get('english') or media.get('title', {}).get('romaji')
                if subtitle:
                    anime_roles.append({
                        'title': character['name']['full'],
                        'image': character['image']['medium'],
                        'subtitle': subtitle,
                    })
            if len(anime_roles) == 8:
                break
        
        def build_base_embed() -> hk.Embed:
            emb = (
                hk.Embed(
                    title=data['name']['full'],
                    url=data.get('siteUrl', ''),
                    color=colors.ANILIST,
                    timestamp=datetime.now().astimezone(),
                )
                .set_thumbnail(data.get('image', {}).get('medium'))
                .set_footer(
                    text="Source: AniList",
                    icon="https://anilist.co/img/icons/android-chrome-512x512.png",
                )
            )
            
            info_fields = []
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
                emb.add_field(name, value, inline=inline)
            
            emb.add_field("Description", description, inline=False)
            
            if non_anime_roles:
                other_roles_list = [role['character'] for role in non_anime_roles if role['character'].strip() != "~!"]
                if other_roles_list:
                    emb.add_field("Other Roles", ", ".join([f"{role}" for role in other_roles_list[:5]]), inline=False)
            
            return emb

        embed = build_base_embed()
        
        if anime_roles:
            card_image_4 = await card_maker(anime_roles[:4], ctx.bot.d.anilist)
            buf4 = BytesIO()
            card_image_4.save(buf4, format='PNG')
            embed.set_image(hk.Bytes(buf4.getvalue(), 'va_card_4.png'))

        swap_embed = None
        if len(anime_roles) > 4:
            swap_embed = build_base_embed()
            card_image_8 = await card_maker(anime_roles[:8], ctx.bot.d.anilist)
            buf8 = BytesIO()
            card_image_8.save(buf8, format='PNG')
            swap_embed.set_image(hk.Bytes(buf8.getvalue(), 'va_card_8.png'))

        view = views.AuthorView(user_id=ctx.author.id)
        if swap_embed:
            view.add_item(
                btns.SwapButton(
                    original_page=embed,
                    swap_page=swap_embed,
                    label1="See more roles",
                    emoji1="⬇",
                    label2="See less roles",
                    emoji2="⬆",
                )
            )
        view.add_item(btns.KillButton())
        
        choice = await ctx.edit_last_response(content=None, embed=embed, components=view)
        await view.start(choice)
        await view.wait()
        
    except Exception as e:
        await ctx.edit_last_response(f"Error: {e}")
    

class AnimeSelect(miru.TextSelect):
    """A text select for Anime search that updates embeds and trailer swap button"""

    def __init__(
        self,
        *,
        options: list[miru.SelectOption],
        placeholder: str = "Select an anime",
    ) -> None:
        super().__init__(options=options, placeholder=placeholder)

    async def callback(self, ctx: miru.ViewContext) -> None:
        selected_id = self.values[0]
        if hasattr(self.view, "pages") and selected_id in self.view.pages:
            new_embed = self.view.pages[selected_id]
            trailer = getattr(self.view, "trailers", {}).get(selected_id, "Couldn't find anything.")

            for child in self.view.children:
                if isinstance(child, btns.SwapButton):
                    child.original_page = new_embed
                    child.swap_page = trailer
                    child.label = child.label1
                    child.emoji = child.emoji1
                    break

            await ctx.edit_response(content=None, embeds=[new_embed], components=self.view)


async def _search_novel(ctx: lb.Context, novel: str):
    """Search a novel on AL"""
    media_list = await ALNovel.from_search_multiple(novel, ctx.bot.d.anilist)

    if not media_list:
        single_res = await ALNovel.from_search(novel, ctx.bot.d.anilist)
        if single_res:
            media_list = [single_res]

    if not media_list:
        await ctx.respond(
            hk.Embed(
                title="NOVEL NOT FOUND",
                color=colors.ERROR,
                description=f"Couldn't find novel `{novel}` 😵",
                timestamp=datetime.now().astimezone(),
            )
        )
        return

    pages = {}
    options = []
    first_page = None

    for i, response in enumerate(media_list[:15]):
        title = (response["title"]["english"] or response["title"]["romaji"])[:99]

        if response.get("description"):
            clean_desc = parse_description(response["description"])
        else:
            clean_desc = "NA"

        rel_year = response.get("startDate", {}).get("year")
        label_text = f"{title} ({rel_year})" if rel_year else title
        label_text = truncate_words(label_text, 100)

        if clean_desc != "NA":
            short_desc = " ".join(clean_desc.split())
            if len(response.get("description", "")) > 75 or len(short_desc) > 75:
                short_desc = truncate_words(short_desc, 75)
        else:
            short_desc = "No description"

        item_id_str = str(response["id"])

        options.append(
            miru.SelectOption(
                label=label_text,
                value=item_id_str,
                description=short_desc,
            )
        )

        embed = (
            hk.Embed(
                title=title,
                url=response["siteUrl"],
                description="\n\n",
                color=colors.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Rating", response.get("meanScore") or "NA")
            .add_field("Genres", ", ".join(response.get("genres", [])[:4]) or "NA")
            .add_field("Status", response.get("status", "NA"), inline=True)
            .add_field(
                "Volumes",
                response.get("volumes") or "NA",
                inline=True,
            )
            .add_field("Summary", clean_desc)
            .set_thumbnail(response.get("coverImage", {}).get("large"))
            .set_image(response.get("bannerImage"))
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        )

        if not i:
            first_page = embed

        pages[item_id_str] = embed

    view = views.SelectView(user_id=ctx.author.id, pages=pages)
    view.add_item(SimpleTextSelect(options=options, placeholder="Select a novel"))
    view.add_item(btns.KillButton())

    choice = await ctx.respond(embed=first_page, components=view)
    await view.start(choice)
    await view.wait()


async def _time_to(ctx: lb.Context, series: str) -> None:
    """Time investment needed by a series and watch order"""
    await ctx.respond(f"{get_random_quote()} {hk.Emoji.parse(emotes.LOADING.value)}")
    try:
        data = await ALAnime.get_anime_data(ctx.bot.d.anilist, search=series)
        media = data.get("Media") if data else None
        if not media:
            await ctx.edit_last_response(
                content=None,
                embed=hk.Embed(
                    title="ANIME NOT FOUND",
                    color=colors.ERROR,
                    description=f"Couldn't find anime `{series}` 😵",
                    timestamp=datetime.now().astimezone(),
                ),
            )
            return

        anime_id = int(media["id"])
        series_list = await ALAnime.format_chronological_order(ctx.bot.d.anilist, anime_id=anime_id)
        if not series_list:
            await ctx.edit_last_response(
                content=None,
                embed=hk.Embed(
                    title="WATCH ORDER NOT FOUND",
                    color=colors.ERROR,
                    description=f"Couldn't find watch order for `{series}` 😵",
                    timestamp=datetime.now().astimezone(),
                ),
            )
            return

        order = " -> ".join(str(entry) for entry in series_list)
        total_time_investment = sum(
            entry.episodes * entry.duration for entry in series_list
        )
        try:
            series_name = find_series_name(
                [entry.title.lower() for entry in series_list]
            ).title()
        except Exception:
            series_name = media.get("title", {}).get("english") or media.get("title", {}).get("romaji") or series.title()

        if not series_name:
            series_name = series.title()

        hours, mins = divmod(total_time_investment, 60)
        time_str = f"{hours} hours, {mins} minutes" if hours else f"{mins} minutes"

        response_text = (
            f"The time investment required for the `{series_name}` series is {time_str}.\n\n"
            f"The suggested watch order, based on release date is as follows:\n{order}"
        )

        if len(response_text) > 2000:
            header = f"The time investment required for the `{series_name}` series is {time_str}.\n\nThe suggested watch order, based on release date is as follows:\n"
            await ctx.edit_last_response(header, flags=hk.MessageFlag.SUPPRESS_EMBEDS)

            curr_chunk = ""
            for entry in series_list:
                item_str = str(entry)
                if len(curr_chunk) + len(item_str) + 4 > 1900:
                    await ctx.respond(curr_chunk, flags=hk.MessageFlag.SUPPRESS_EMBEDS)
                    curr_chunk = item_str
                else:
                    if curr_chunk:
                        curr_chunk += " -> " + item_str
                    else:
                        curr_chunk = item_str
            if curr_chunk:
                await ctx.respond(curr_chunk, flags=hk.MessageFlag.SUPPRESS_EMBEDS)
        else:
            await ctx.edit_last_response(
                response_text,
                flags=hk.MessageFlag.SUPPRESS_EMBEDS,
            )

    except Exception as e:
        await ctx.edit_last_response(f"Error fetching watch order: {e}")


async def _search_anime(ctx, anime: str):
    """Search an anime on AL"""
    media_list = await ALAnime.from_search_multiple(anime, ctx.bot.d.anilist)

    if not media_list:
        return await ctx.respond(
            hk.Embed(
                title="ANIME NOT FOUND",
                color=colors.ERROR,
                description=f"Couldn't find anime `{anime}` 😵",
                timestamp=datetime.now().astimezone(),
            )
        )

    pages = {}
    trailers_dict = {}
    options = []
    first_page = None
    first_trailer = "Couldn't find anything."

    for i, response in enumerate(media_list[:15]):
        title = response["title"]["english"] or response["title"]["romaji"]

        no_of_items = response.get("episodes") if response.get("episodes") else "NA"

        if isinstance(response.get("episodes"), int) and no_of_items == 1:
            no_of_items = (
                verbose_timedelta(timedelta(minutes=response["duration"]))
                if response.get("duration")
                else "NA"
            )
        elif response.get("nextAiringEpisode"):
            if no_of_items == "NA":
                no_of_items = f"{response['nextAiringEpisode']['episode']-1}/??"
            else:
                no_of_items = f"{response['nextAiringEpisode']['episode']-1}/{no_of_items}"

        if response.get("description"):
            clean_desc = parse_description(response["description"])
        else:
            clean_desc = "NA"

        rel_year = response.get("startDate", {}).get("year")
        label_text = f"{title} ({rel_year})" if rel_year else title
        label_text = truncate_words(label_text, 100)

        if clean_desc != "NA":
            short_desc = " ".join(clean_desc.split())
            if len(response.get("description", "")) > 75 or len(short_desc) > 75:
                short_desc = truncate_words(short_desc, 75)
        else:
            short_desc = "No description"

        if response.get("studios") and response["studios"].get("nodes"):
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
                "Rating", response.get("meanScore") or "NA"
            )
            .add_field("Genres", ", ".join(response.get("genres", [])[:4]) or "NA")
            .add_field("Status", response.get("status", "NA").replace("_", " "), inline=True)
            .add_field(
                "Episodes" if response.get("episodes") != 1 else "Duration",
                no_of_items,
                inline=True,
            )
            .add_field("Studio", studios, inline=True)
            .add_field("Summary", clean_desc)
            .set_thumbnail(response.get("coverImage", {}).get("large"))
            .set_image(response.get("bannerImage"))
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        )

        trailer = "Couldn't find anything."
        if response.get("trailer") and response["trailer"].get("site") and response["trailer"].get("id"):
            if response["trailer"]["site"] == "youtube":
                trailer = f"https://youtube.com/watch?v={response['trailer']['id']}"
            else:
                trailer = f"https://{response['trailer']['site']}.com/video/{response['trailer']['id']}"

        item_id_str = str(response["id"])
        if not i:
            first_page = embed
            first_trailer = trailer

        options.append(
            miru.SelectOption(
                label=label_text,
                value=item_id_str,
                description=short_desc,
            )
        )
        pages[item_id_str] = embed
        trailers_dict[item_id_str] = trailer

    view = views.SelectView(user_id=ctx.author.id, pages=pages)
    view.trailers = trailers_dict
    view.add_item(AnimeSelect(options=options, placeholder="Select an anime"))
    view.add_item(
        btns.SwapButton(
            swap_page=first_trailer,
            original_page=first_page,
            label1="Trailer",
            emoji1=hk.Emoji.parse(emotes.YOUTUBE.value),
            emoji2=hk.Emoji.parse("🔍"),
        )
    )
    view.add_item(btns.KillButton())

    choice = await ctx.respond(embed=first_page, components=view)
    await view.start(choice)
    await view.wait()
    # except Exception as e:
    #     print(e)


async def _search_manga(ctx, manga: str):
    """Search a manga on AL"""
    try:
        series_list = await ALManga.from_search_multiple(manga, ctx.bot.d.anilist)
        if not series_list:
            await ctx.respond(
                hk.Embed(
                    title="MANGA NOT FOUND",
                    color=colors.ERROR,
                    description=f"Couldn't find manga `{manga}` 😵",
                    timestamp=datetime.now().astimezone(),
                )
            )
            return

        pages = {}
        options = []
        first_page = None

        for i, series in enumerate(series_list[:15]):
            title = (series["title"]["english"] or series["title"]["romaji"])[:99]
            no_of_items = series.get("chapters") or series.get("episodes") or "NA"

            if series.get("description"):
                description = parse_description(series["description"])
            else:
                description = "NA"

            embed = (
                hk.Embed(
                    title=title,
                    url=series["siteUrl"],
                    description="\n\n",
                    color=colors.ANILIST,
                    timestamp=datetime.now().astimezone(),
                )
                .add_field("Rating", series.get("meanScore") or "NA")
                .add_field("Genres", ", ".join(series.get("genres", [])[:4]) if series.get("genres") else "NA")
                .add_field("Status", series.get("status", "NA").replace("_", " ") if series.get("status") else "NA", inline=True)
                .add_field(
                    "Chapters",
                    no_of_items,
                    inline=True,
                )
                .add_field("Summary", description)
                .set_thumbnail(series["coverImage"]["large"] if series.get("coverImage") else None)
                .set_image(series.get("bannerImage"))
                .set_footer(
                    text="Source: AniList",
                    icon="https://anilist.co/img/icons/android-chrome-512x512.png",
                )
            )

            series_id_str = str(series["id"])
            if not i:
                first_page = embed

            opt_desc = f"Rating: {series.get('meanScore') or 'NA'} | Status: {series.get('status', 'NA').replace('_', ' ') if series.get('status') else 'NA'}"
            options.append(
                miru.SelectOption(
                    label=title[:100],
                    value=series_id_str,
                    description=opt_desc[:100],
                )
            )
            pages[series_id_str] = embed

        view = views.SelectView(user_id=ctx.author.id, pages=pages)
        view.add_item(SimpleTextSelect(options=options, placeholder="Other manga"))
        view.add_item(btns.KillButton())

        resp = await ctx.respond(content=None, embed=first_page, components=view)
        await view.start(resp)
        await view.wait()

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
            characters = await ALCharacter.get_birthday_characters(ctx.bot.d.anilist)
            
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
                user_id=ctx.author.id, session=ctx.bot.d.anilist
            )
            
            view.add_item(
                CharacterSelect(
                    options=options, 
                    placeholder="Select character"
                )
            )
            view.add_item(btns.KillButton())
            
            first_chara = await ALCharacter.from_id(int(characters[0]["id"]), ctx.bot.d.anilist)
            first_embed = await first_chara.make_embed() if first_chara else None

            resp = await ctx.respond(embed=first_embed, components=view)
            await view.start(resp)
            await view.wait()
            
        except Exception as e:
            await ctx.respond(f"Error getting birthday characters: {e}")
        return
    
    if not series:
        # General character search - show dropdown with multiple results
        try:
            characters = await ALCharacter.from_search_multiple(query, ctx.bot.d.anilist, per_page=25)
            
            if not characters:
                await ctx.respond(
                    hk.Embed(
                        title="CHARACTER NOT FOUND",
                        color=colors.ERROR,
                        description=f"Couldn't find character `{query}` 😵",
                        timestamp=datetime.now().astimezone(),
                    )
                )
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
                user_id=ctx.author.id, session=ctx.bot.d.anilist
            )
            
            view.add_item(
                CharacterSelect(
                    options=options, 
                    placeholder=f"Select character"
                )
            )
            view.add_item(btns.KillButton())
            
            first_chara = await ALCharacter.from_id(int(characters[0]["id"]), ctx.bot.d.anilist)
            first_embed = await first_chara.make_embed() if first_chara else None

            resp = await ctx.respond(embed=first_embed, components=view)
            await view.start(resp)
            await view.wait()
            
        except Exception as e:
            await ctx.respond(f"Error searching characters: {e}")
        return

    else:
        # Series-specific character search
        try:
            title, characters = await ALCharacter.from_series_characters(series, ctx.bot.d.anilist)
            
            if not title or not characters:
                await ctx.respond(
                    hk.Embed(
                        title="CHARACTER NOT FOUND",
                        color=colors.ERROR,
                        description=f"Couldn't find series `{series}` or no characters found 😵",
                        timestamp=datetime.now().astimezone(),
                    )
                )
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
                    user_id=ctx.author.id, session=ctx.bot.d.anilist
                )
                
                view.add_item(
                    CharacterSelect(
                        options=options, 
                        placeholder=f"Select {title[:50]} character"
                    )
                )
                view.add_item(btns.KillButton())
                
                first_chara = await ALCharacter.from_id(int(characters[0]["id"]), ctx.bot.d.anilist)
                first_embed = await first_chara.make_embed() if first_chara else None

                resp = await ctx.respond(embed=first_embed, components=view)
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
                    user_id=ctx.author.id, session=ctx.bot.d.anilist
                )
                
                view.add_item(
                    CharacterSelect(
                        options=options, 
                        placeholder=f"Select character from '{title[:50]}'"
                    )
                )
                view.add_item(btns.KillButton())
                
                first_chara = await ALCharacter.from_id(int(similar_characters[0]["id"]), ctx.bot.d.anilist)
                first_embed = await first_chara.make_embed() if first_chara else None

                resp = await ctx.respond(embed=first_embed, components=view)
                await view.start(resp)
                await view.wait()

        except Exception as e:
            await ctx.respond(f"Error searching series characters: {e}")





def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(al_listener)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(al_listener)
