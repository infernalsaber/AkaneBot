import typing as t
import re

import lightbulb as lb
import hikari as hk
from rapidfuzz import process
from rapidfuzz.utils import default_process
import bs4

from functions import buttons as btns
from functions import views as views
from functions.components import NavSelector
from functions.hakush import HSRCharacter, ZZZCharacter, WuwaCharacter
from functions.models import ColorPalette as colors

gacha = lb.Plugin("Gacha", "Misc. stuff", include_datastore=True)
gacha.d.help = True
gacha.d.help_image = "https://i.imgur.com/YxvyvaF.png"
gacha.d.help_emoji = "🎲"



@gacha.command
@lb.option("agent", "The agent to search for", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command(
    "zzz",
    "Search for a Zenless Agent",
    aliases=["zenless", "zenlesszonezero"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand)
async def zzz_chara(ctx: lb.Context, agent: str) -> None:
    chara: ZZZCharacter = await ZZZCharacter.from_search(agent, ctx.bot.d.aio_session)

    pages, options = await chara.make_pages()

    components = {}
    for page_name, page_value in pages.items():
        if len(page_value) > 1:
            components[page_name] = [
                btns.CustomPrevButton(),
                btns.CustomNextButton(),
            ]
        else:
            components[page_name] = []

    view = views.SelectNavigator(
        user_id=ctx.author.id,
        dropdown_options=pages,
        dropdown_components=components,
        first_page="Story",
    )
    view.add_item(NavSelector(options=options, placeholder="More Info"))
    view.add_item(btns.KillNavButton())
    await view.send(ctx.channel_id)



@gacha.command
@lb.command("zzz", "Base command for ZZZ slash commands")
@lb.implements(lb.SlashCommandGroup)
async def zzz_slash(ctx: lb.SlashContext) -> None:
    pass


@zzz_slash.child
@lb.option(
    "disc",
    "The disc drive to search for",
    autocomplete=True
)
@lb.command("disc", "Search for a disc drive", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def disc_search(ctx: lb.Context, disc: str) -> None:
    
    await ctx.respond('Searching the inter-knot...')
    base_url = "https://www.prydwen.gg"
    
    disk_drive_raw = await ctx.bot.d.aio_session.get(f"{base_url}/zenless/disk-drives/")
    disk_drives_data = parse_prydwen_disc_info(await disk_drive_raw.text())
    
    for disk_drive in disk_drives_data:
        if disk_drive["name"].lower() == disc.lower():
            await ctx.edit_last_response(
                content=None,
                embed=hk.Embed(
                    title=disk_drive["name"],
                    description=format_disc_info(disk_drive['description']),
                    color=colors.ZZZ_DISK
                )
                .set_thumbnail(f"{base_url}{disk_drive['image']}")
                .set_footer(text=f"Via: Prydwen.gg", icon='https://www.prydwen.gg/static/c20213ad82f52dcc3a6670bb5006ef1e/dbb7e/prydwen_logo_min.webp')
            )

@zzz_slash.child
@lb.option(
    "character",
    "The character to search",
    autocomplete=True
)
@lb.command("agent", "Search for a zzz agent", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def agent_search(ctx: lb.Context, character: str) -> None:
        
    chara: ZZZCharacter = await ZZZCharacter.from_search(character, ctx.bot.d.aio_session)
    pages, options = await chara.make_pages()

    components = {}
    for page_name, page_value in pages.items():
        if len(page_value) > 1:
            components[page_name] = [
                btns.CustomPrevButton(),
                btns.CustomNextButton(),
            ]
        else:
            components[page_name] = []

    view = views.SelectNavigator(
        user_id=ctx.author.id,
        dropdown_options=pages,
        dropdown_components=components,
        first_page="Story",
    )
    view.add_item(NavSelector(options=options, placeholder="More Info"))
    view.add_item(btns.KillNavButton())
    await view.send(ctx.interaction, responded=True)

@zzz_slash.child
@lb.option(
    "engine",
    "The w-engine to search for",
    autocomplete=True
)
@lb.command("engine", "Search for a w-engine", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashSubCommand)
async def w_engine_search(ctx: lb.Context, engine: str) -> None:
    
    
    await ctx.respond('Searching the inter-knot...')
    
    base_url = "https://www.prydwen.gg"
    
    w_engine_data = await ctx.bot.d.aio_session.get(f"{base_url}/page-data/sq/d/1774289164.json")
    w_engine_data = await w_engine_data.json()
    w_engine_data = w_engine_data["data"]["allContentfulZzzEngine"]["nodes"]
    
    for engine_data in w_engine_data:
        if engine_data["name"].lower() == engine.lower():
            await ctx.edit_last_response(
                content=None,
                embed=hk.Embed(
                    url=f"{base_url}/zenless/w-engines",
                    title=engine_data["name"],
                    description=parse_prydwen_description(engine_data["description"]["raw"]),
                    color=colors.ZZZ_S_ENGINE if engine_data["rarity"] == "S" else colors.ZZZ_A_ENGINE
                )
                .add_field(name='Statistics', value=f'Attack: {engine_data["stats"]["max_atk"]} | {engine_data["stats"]["stat"]}: {engine_data["stats"]["max_special"]}')
                .add_field(name="Rarity", value=engine_data["rarity"], inline=True)
                .add_field(name="Type", value=engine_data["type"], inline=True)
                .set_thumbnail(f"{base_url}{engine_data['image']['localFile']['childImageSharp']['gatsbyImageData']['images']['fallback']['src']}")
                .set_footer(text=f"Via: Prydwen.gg", icon='https://www.prydwen.gg/static/c20213ad82f52dcc3a6670bb5006ef1e/dbb7e/prydwen_logo_min.webp')
            )


@gacha.command
@lb.option("character", "The character to search for", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command(
    "hsr",
    "Search for an HSR Character",
    aliases=["honkai", "honkaistarail"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand)
async def hsr_chara(ctx: lb.Context, character: str) -> None:
    chara: HSRCharacter = await HSRCharacter.from_search(character, ctx.bot.d.aio_session)

    pages, options = await chara.make_pages()

    components = {}
    for page_name, page_value in pages.items():
        if len(page_value) > 1:
            components[page_name] = [
                btns.CustomPrevButton(),
                btns.CustomNextButton(),
            ]
        else:
            components[page_name] = []

    view = views.SelectNavigator(
        user_id=ctx.author.id,
        dropdown_options=pages,
        dropdown_components=components,
        first_page="Story",
    )
    view.add_item(NavSelector(options=options, placeholder="More Info"))
    view.add_item(btns.KillNavButton())
    await view.send(ctx.channel_id)


@gacha.command
@lb.option("character", "The character to search for", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command(
    "wuwa",
    "Search for an Wuthering Waves Character",
    aliases=["ww", "wuthering"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand)
async def wuwa_chara(ctx: lb.Context, character: str) -> None:
    chara: WuwaCharacter = await WuwaCharacter.from_search(character, ctx.bot.d.aio_session)
    
    pages, options = await chara.make_pages()

    components = {}
    
    try:
    
        for page_name, page_value in pages.items():
            if len(page_value) > 1:
                components[page_name] = [
                    btns.CustomPrevButton(),
                    btns.CustomNextButton(),
                ]
            else:
                components[page_name] = []

        view = views.SelectNavigator(
            user_id=ctx.author.id,
            dropdown_options=pages,
            dropdown_components=components,
            first_page="Story",
        )
        view.add_item(NavSelector(options=options, placeholder="More Info"))
        view.add_item(btns.KillNavButton())
        await view.send(ctx.channel_id)
    
    except Exception as e:
        await ctx.respond(f"Error: {e}")


@agent_search.autocomplete("character")
async def agent_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    url = "https://api.hakush.in/zzz/data/character.json"
    
    agent_data = await interaction.app.d.aio_session.get(url)
    agent_data = await agent_data.json()
    
    chara_codes = list(agent_data.keys())
    name_code_mapping = {}

    for code in chara_codes:
        name_code_mapping.update(
            {agent_data[code].get("EN") or agent_data[code]["en"]: code}
        )
    
    if option.value in ["", None]:
        return sorted(name_code_mapping.keys())[:24]

    close_matches = process.extract(
        option.value,
        name_code_mapping.keys(),
        processor=default_process,
        score_cutoff=85,
        limit=None,
    )

    possible_agents: t.Sequence = []

    if close_matches:
        possible_agents = [f"{i}" for i, *_ in close_matches]

    return possible_agents[:24]

@w_engine_search.autocomplete("engine")
async def w_engine_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    base_url = "https://www.prydwen.gg"
    
    w_engine_data = await interaction.app.d.aio_session.get(f"{base_url}/page-data/sq/d/1774289164.json")
    w_engine_data = await w_engine_data.json()
    w_engine_data = w_engine_data["data"]["allContentfulZzzEngine"]["nodes"]
    
    engine_names = [engine["name"] for engine in w_engine_data]
    
    if option.value in ["", None]:
        return engine_names[:24]
    
    close_matches = process.extract(
        option.value,
        engine_names,
        score_cutoff=85,
        limit=None,
        processor=default_process,
    )
    
    possible_w_engines: t.Sequence = []

    if close_matches:
        possible_w_engines = [f"{i}" for i, *_ in close_matches]

    return possible_w_engines[:24]

@disc_search.autocomplete("disc")
async def disc_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    base_url = "https://www.prydwen.gg"
    
    disk_drive_raw = await interaction.app.d.aio_session.get(f"{base_url}/zenless/disk-drives/")
    disk_drives_data = parse_prydwen_disc_info(await disk_drive_raw.text())
    
    disk_drive_names = [disk_drive["name"] for disk_drive in disk_drives_data]
    
    
    if option.value in ["", None]:
        return disk_drive_names[:24]
    
    close_matches = process.extract(
        option.value,
        disk_drive_names,
        score_cutoff=85,
        limit=None,
        processor=default_process,
    )
    
    possible_disc_drives: t.Sequence = []
    
    if close_matches:
        possible_disc_drives = [f"{i}" for i, *_ in close_matches]
    
    return possible_disc_drives[:24]


def parse_prydwen_description(description: str) -> str:
    import json
    
    # Parse the JSON description
    data = json.loads(description)
    
    def extract_text_from_content(content_list):
        text_parts = []
        for item in content_list:
            if item.get("nodeType") == "text":
                value = item.get("value", "")
                marks = item.get("marks", [])
                
                # Apply bold formatting if present
                if any(mark.get("type") == "bold" for mark in marks):
                    value = f"**{value}**"
                
                text_parts.append(value)
            elif item.get("nodeType") == "paragraph" and "content" in item:
                text_parts.append(extract_text_from_content(item["content"]))
        
        return "".join(text_parts)
    
    # Extract text from the main content
    if "content" in data:
        paragraphs = []
        for paragraph in data["content"]:
            if paragraph.get("nodeType") == "paragraph" and "content" in paragraph:
                paragraph_text = extract_text_from_content(paragraph["content"])
                if paragraph_text.strip():
                    paragraphs.append(paragraph_text)
        
        return "\n\n".join(paragraphs)
    
    return ""

def parse_prydwen_disc_info(page_html: str) -> dict:
    soup = bs4.BeautifulSoup(page_html, 'lxml')
    
    discs_info = []
    
    discs_info_raw = soup.find_all('div', class_='zzz-disk-set')

    for disc_info_raw in discs_info_raw:
        disc_info = {}
        disc_info['name'] = disc_info_raw.find('div', class_='zzz-info').text.strip()
        disc_info['description'] = disc_info_raw.find('div', class_='zzz-disk-content').text.strip()
        disc_info['image'] = disc_info_raw.find_all('img')[1]['data-src']
        discs_info.append(disc_info)
    
    return discs_info


def format_disc_info(text: str) -> str:
    # Configurable highlight rules: phrase -> (start_ansi, end_ansi)
    highlight_rules = {
        r"electric dmg": ("\u001b[0;34m", "\u001b[0;37m"),
        r"shocked": ("\u001b[0;34m", "\u001b[0;37m"),
        r"freeze": ("\u001b[0;36m", "\u001b[0;37m"),
        r"shatter": ("\u001b[0;36m", "\u001b[0;37m"),
        r"fire dmg": ("\u001b[0;31m", "\u001b[0;37m"),
        r"burning": ("\u001b[0;31m", "\u001b[0;37m"),
        r"physical dmg": ("\u001b[0;33m", "\u001b[0;37m"),
        r"daze": ("\u001b[0;33m", "\u001b[0;37m"),
        r"assault": ("\u001b[0;33m", "\u001b[0;37m"),
        r"ether dmg": ("\u001b[0;35m", "\u001b[0;37m"),
        r"corruption": ("\u001b[0;35m", "\u001b[0;37m"),
    }
    # Number highlighting: match numbers with optional +/-, %, . etc.
    number_pattern = re.compile(r"([+-]?\d+\.?\d*%?)")
    number_ansi_start = "\u001b[0;33m"
    number_ansi_end = "\u001b[0;37m"

    descr = text.replace('(2)', '').split('(4)')

    def apply_highlights(s: str) -> str:
        # Highlight numbers
        s = number_pattern.sub(lambda m: f"{number_ansi_start}{m.group(1)}{number_ansi_end}", s)
        # Highlight phrases
        for phrase, (start_ansi, end_ansi) in highlight_rules.items():
            s = re.sub(phrase, lambda m: f"{start_ansi}{m.group(0)}{end_ansi}", s, flags=re.IGNORECASE)
        return s

    desc0 = apply_highlights(descr[0])
    desc1 = apply_highlights(descr[1])

    desc = f"```ansi\n(2) {desc0}\n\n(4) {desc1}```"
    return desc

def load(bot: lb.BotApp) -> None:
    # Load the plugin
    bot.add_plugin(gacha)


def unload(bot: lb.BotApp) -> None:
    # Unload the plugin
    bot.remove_plugin(gacha)
