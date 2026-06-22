"""Visual novel (VNDB) related commands"""

import collections
import re
from datetime import datetime
from operator import itemgetter

import hikari as hk
import lightbulb as lb
import miru
import pandas as pd

from extensions.adata import al_search
from utils import buttons as btns
from utils import views as views
from utils.components import SimpleTextSelect
from utils.misc import dlogger, verbose_date
from utils.models import ColorPalette as colors

vn_listener = lb.Plugin(
    "VN",
    "Search functions for visual novels, characters, traits and tags from VNDB",
    include_datastore=True,
)
vn_listener.d.help = True
vn_listener.d.help_emoji = "📖"


vndb_pattern = re.compile(r"\b(https?:\/\/)?(www.)?vndb.org\/[a-z]\/(\d+)")


# ============ LOOKUP SLASH SUBCOMMANDS (attached to al_search in adata) ============

@al_search.child
@lb.option(
    "visual_novel",
    "The visual novel to search for",
    # autocomplete=True
)
@lb.command("visualnovel", "Search for a visual novel on VNDB", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def vn_search_slash(ctx: lb.Context, visual_novel: str) -> None:
    """Search for a visual novel on AL"""
    return await _search_vn(ctx, visual_novel)


@al_search.child
@lb.option(
    "character",
    "The character to search for"
)
@lb.command("vncharacter", "Search for a character on VNDB", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def vn_character_search_slash(ctx: lb.SlashContext, character: str) -> None:
    """Search for a character on VNDB"""
    return await _search_vnchara(ctx, character)


@al_search.child
@lb.option(
    "trait",
    "The trait to search for"
)
@lb.command("vntrait", "Search for a trait on VNDB", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def vn_trait_search_slash(ctx: lb.Context, trait: str) -> None:
    """Search for a trait on VNDB"""
    return await _search_vntrait(ctx, trait)


@al_search.child
@lb.option(
    "tag",
    "The tag to search for"
)
@lb.command("vntag", "Search for a tag on VNDB", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def vn_tag_search_slash(ctx: lb.SlashContext, tag: str) -> None:
    """Search for a tag on VNDB"""
    return await _search_vntag(ctx, tag)


# ============ PREFIX COMMANDS ============

@vn_listener.command
@lb.option(
    "query", "The vn to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("visualnovel", "Search a vn", pass_options=True, aliases=["vn"])
@lb.implements(lb.PrefixCommand)
async def vn_search_prefix(ctx: lb.PrefixContext, query: str):
    """Search for a visual novel via VNDB

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The vn to search for
    """

    await _search_vn(ctx, query)


@vn_listener.command
@lb.option(
    "query", "The vn trait to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vntrait", "Search a vn", pass_options=True, aliases=["trait"])
@lb.implements(lb.PrefixCommand)
async def vn_trait_search_prefix(ctx: lb.PrefixContext, query: str):
    """Search for a visual novel character trait via VNDB

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The vn trait to search for
    """

    await _search_vntrait(ctx, query)


@vn_listener.command
@lb.option(
    "query", "The vntag to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vntag", "Search a vntag", pass_options=True, aliases=["tag"])
@lb.implements(lb.PrefixCommand)
async def vn_tag_search_prefix(ctx: lb.PrefixContext, query: str):
    """Search for a visual novel tag via VNDB

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The vn tag to search for
    """

    await _search_vntag(ctx, query)


@vn_listener.command
@lb.option(
    "query", "The vnchara to search", modifier=lb.commands.OptionModifier.CONSUME_REST
)
@lb.command("vnc", "Search a vn character", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def vn_chara_search_prefix(ctx: lb.PrefixContext, query: str):
    """Search for a visual novel character via VNDB

    Args:
        ctx (lb.PrefixContext): The context
        query (str): The character to search for
    """

    await _search_vnchara(ctx, query)


# ============ TRAIT MAP COMMANDS ============

@vn_listener.command
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


@vn_listener.command
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


@vn_listener.command
@lb.add_checks(lb.owner_only)
@lb.command("traits", "Show all the traits")
@lb.implements(lb.PrefixCommand)
async def show_traits(ctx: lb.PrefixContext):
    """Show all the trait maps"""
    await ctx.respond(
        f'```{pd.read_sql("SELECT * FROM traitmap", ctx.bot.d.con).to_string(index=False)}```'
    )


# ============ HELPERS ============

async def _fetch_trait_map(user: str) -> str:
    """Search if there's a trait map for a query"""
    db = vn_listener.bot.d.con
    cursor = db.cursor()
    cursor.execute("SELECT trait FROM traitmap WHERE user=?", (user,))
    return cursor.fetchone()


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


# ============ INTERNAL SEARCH FUNCTIONS ============

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
        req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data)

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
            return await ctx.respond(
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
                if (
                    tag["category"] == "cont" and tag["spoiler"] != 2
                ):  # 0 = not a spoiler, 1 = minor spoiler, 2 - major.
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
            time = len_map.get(int(req["results"][0]["length"]), "NA")

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
        import traceback
        await dlogger(
            ctx.bot, f"VNDB search failed: ```{traceback.format_exc()}```"
        )


async def _search_vnchara(ctx: lb.Context, query: str):
    """Search a vn character"""
    url = "https://api.vndb.org/kana/character"
    headers = {"Content-Type": "application/json"}
    data = {
        "filters": ["search", "=", query],
        "fields": "name, description, age, sex,  image.url, traits.name, traits.group_name, vns.title, birthday",
    }

    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data)

    if not req.ok:
        await ctx.respond("Couldn't find the character you asked for.")
        return

    req = await req.json()

    if not req["results"]:
        return await ctx.respond(
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
    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data)

    if not req.ok:
        await ctx.respond("Couldn't find the tag you asked for.")
        return

    req = await req.json()

    if not req["results"]:
        return await ctx.respond(
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

    req = await ctx.bot.d.aio_session.post(url, headers=headers, json=data)

    if not req.ok:
        await ctx.respond("Couldn't find the trait you asked for.")
        return

    req = await req.json()

    if not req["results"]:
        return await ctx.respond(
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


# ============ STARTUP ============

@vn_listener.listener(hk.StartedEvent)
async def on_starting(event: hk.StartedEvent) -> None:
    """Create traitmap table on bot start"""

    conn = vn_listener.bot.d.con
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


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(vn_listener)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(vn_listener)
