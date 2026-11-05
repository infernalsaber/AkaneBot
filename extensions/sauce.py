"""Search the source of a given image"""


import asyncio
import io
import logging
import os
import re
import typing as t
from collections import Counter
from datetime import datetime
from urllib.parse import quote, urlparse

import aiohttp
import av
import dotenv
import hikari as hk
import lightbulb as lb
import miru
import yarl
from miru.ext import nav

from utils.anilist import ALManga
from utils.buttons import (
    GenericButton,
    KillButton,
    KillNavButton,
    NavButton,
    SwapButton,
    SwapNaviButton
)
from utils.emotes_helper import check_if_known_emoji_provider
from utils.models import ColorPalette as colors
from utils.models import EmoteCollection as emotes
from utils.misc import (
    check_if_url,
    get_random_quote,
    iso_to_timestamp,
    tenor_link_from_gif
)
from utils.views import AuthorNavi, AuthorView

dotenv.load_dotenv()

SAUCENAO_KEY = os.getenv("SAUCENAO_KEY")

logger = logging.getLogger(__name__)

IMAGE_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"]
MAX_MEDIA_SIZE = 100 * 1024 * 1024
GIF_PROVIDERS = ["Tenor", "Klipy", "GIPHY"]
TWITTER_HOSTS = ["x.com", "twitter.com", "fixupx.com", "fxtwitter.com", "vxtwitter.com", "fixvx.com"]

sauce_plugin = lb.Plugin(
    "Sauce", "Finding the source of an image", include_datastore=True
)
sauce_plugin.d.help_image = "https://i.imgur.com/YxvyvaF.png"
sauce_plugin.d.help_emoji = "🔍"
sauce_plugin.d.help = True


@sauce_plugin.command
@lb.add_cooldown(length=86400, uses=7, bucket=lb.UserBucket)
@lb.add_cooldown(length=86400, uses=10, bucket=lb.GuildBucket)
@lb.command("User pfp Sauce", "Sauce of user pfp", auto_defer=True, ephemeral=True)
@lb.implements(lb.UserCommand)
async def pfp_sauce(ctx: lb.UserContext):
    """Find the sauce of a user's pfp

    Args:
        ctx (lb.UserContext): The context the command is invoked in
    """

    url = await _find_the_url(ctx)

    if url["errorMessage"]:
        await ctx.respond(url["errorMessage"])
        return

    params = {
        "api_key": SAUCENAO_KEY,
        "output_type": 2,
        "numres": 5,
        "url": url["url"],
    }

    async with ctx.bot.d.aio_session.get(
        "https://saucenao.com/search.php?", params=params
    ) as res:
        if res.ok:
            res = await res.json()

            if res["header"]["status"] < 0:
                logger.error(f"SauceNAO error: {res['header']['message']}")
                await ctx.respond(f"SauceNAO error (status {res['header']['status']})")
                return

            try:
                embed, view = await _complex_parsing(ctx, res["results"][0])
                if float(res["results"][0]["header"]["similarity"]) < 60.0:
                    # url["url"] = url["url"].split("?")[0]
                    view.add_item(
                        GenericButton(
                            url=f"https://yandex.com/images/search?url={quote(url['url'])}&rpt=imageview",
                            label="Search Yandex",
                        )
                    )
                await ctx.respond(
                    content=f"User: {ctx.options.target.mention}",
                    embed=embed,
                    components=view,
                )
            except Exception:
                embed, view = await _simple_parsing(ctx, res["results"][0])
                await ctx.respond(
                    embed=embed,
                    components=view,
                )
                logger.error(f"Sauce parser failed, json returned: {res}")

        else:
            await ctx.respond(f"Ran into en error, `code : {res.status}`")


@sauce_plugin.command
@lb.add_cooldown(length=86400, uses=10, bucket=lb.UserBucket)
@lb.add_cooldown(length=86400, uses=20, bucket=lb.GuildBucket)
@lb.command("Find the Sauce", "Search the sauce of the image", auto_defer=False)
@lb.implements(lb.MessageCommand)
async def find_sauce_menu(ctx: lb.MessageContext):
    """Find the image from a message and then its sauce

    Args:
        ctx (lb.MessageContext): The context the command is invoked in
    """

    message_link = ctx.options["target"].make_link(ctx.guild_id)

    ctx, url = await _find_the_url(ctx)

    if not url["errorMessage"]:
        link = url["url"]
    elif ctx.responses:  # Reuse the dropdown/deferred message
        await ctx.interaction.edit_initial_response(
            url["errorMessage"], components=None, attachments=None
        )
        return
    else:
        await ctx.respond(url["errorMessage"])
        return

    if not link:  # Dropdown timed out
        return

    params = {
        "api_key": SAUCENAO_KEY,
        "output_type": 2,
        "numres": 5,
        "url": link,
    }

    async with ctx.bot.d.aio_session.get(
        "https://saucenao.com/search.php?", params=params
    ) as res:
        if res.ok:
            res = await res.json()

            if res["header"]["status"] < 0:
                logger.error(f"SauceNAO error: {res['header']['message']}")
                await ctx.interaction.edit_initial_response(
                    f"SauceNAO error (status {res['header']['status']})",
                    components=None,
                    attachments=None,
                )
                return

            try:
                embed, view = await _complex_parsing(ctx, res["results"][0])

                if float(res["results"][0]["header"]["similarity"]) < 60.0:
                    warning_embed = hk.Embed(
                        title="Possible false match",
                        description=(
                            "We might have encountered a false match."
                            "\n\nFalse matches often contain NSFW matches or "
                            "in rarer cases, what you're actually looking for."
                            "\nPlease use the ❌ or Go Back button should that happen."
                        ),
                        color=colors.WARN,
                        timestamp=datetime.now().astimezone(),
                    )
                    view = AuthorNavi(
                        pages=[
                            nav.Page(content=message_link, embed=warning_embed),
                            nav.Page(
                                content=message_link,
                                embed=embed,
                            ),
                        ],
                        buttons=[
                            SwapNaviButton(
                                labels=["Show anyway", "Go Back"],
                                emojis=[
                                    None,
                                    hk.Emoji.parse("<:previous:1136984315415236648>"),
                                ],
                            ),
                            NavButton(
                                url=f"https://yandex.com/images/search?url={quote(url['url'])}&rpt=imageview",
                                label="Search Yandex",
                            ),
                            KillNavButton(style=hk.ButtonStyle.SECONDARY),
                        ],
                        user_id=ctx.author.id,
                    )
                    # What view.send() does, but on the existing message
                    for item in view.children:
                        if isinstance(item, nav.NavItem):
                            await item.before_page_change()
                    choice = await ctx.interaction.edit_initial_response(
                        content=message_link,
                        embed=warning_embed,
                        components=view,
                        attachments=None,
                    )
                    await view.start(choice)

                else:
                    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                    view.clean_items = False
                    choice = await ctx.interaction.edit_initial_response(
                        content=message_link,
                        embed=embed,
                        components=view,
                        attachments=None,
                    )
                    await view.start(choice)
                    await view.wait()
            except Exception as e:
                logger.error(f"Sauce parser failed, json returned: {res}")
                embed, view = await _simple_parsing(ctx, res["results"][0])
                view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                choice = await ctx.interaction.edit_initial_response(
                    content=None, embed=embed, components=view, attachments=None
                )
                # await ctx.respond(e)
                await view.start(choice)
                await view.wait()
        else:
            await ctx.interaction.edit_initial_response(
                f"Ran into en error, `code : {res.status}`",
                components=None,
                attachments=None,
            )


@sauce_plugin.command
@lb.set_help("**Find the source of an image using SauceNAO (default) or Trace.Moe**")
@lb.option(
    "service",
    "The service to use to search for it",
    required=False,
    choices=["SauceNAO", "TraceMoe"],
)
@lb.option(
    "link",
    "The link of the image to find the sauce of",
)
@lb.command("sauce", "Show ya sauce for the image", pass_options=True, auto_defer=True)
@lb.implements(lb.SlashCommand)
async def find_sauce(
    ctx: lb.Context, link: str, service: t.Optional[str] = None
) -> None:
    """Find the sauce of an image

    Args:
        ctx (lb.Context): The context the command is invoked in
        link (str): The url of the image
        service (str, t.Optional): The service to choose. Defaults to None.
    """

    if _is_tenor_link(link):
        await ctx.respond(
            "⚠️ Tenor links have to be scraped and can be unreliable, use **Find the Sauce** "
            f"on a message with the GIF instead {hk.Emoji.parse(emotes.LOADING.value)}"
        )
    else:
        await ctx.respond(f"{get_random_quote()} {hk.Emoji.parse(emotes.LOADING.value)}")

    url = await _find_the_url(ctx)

    if not url["errorMessage"]:
        link = url["url"]
    else:
        await ctx.edit_last_response(url["errorMessage"])
        return

    params = {"api_key": SAUCENAO_KEY, "output_type": 2, "numres": 5, "url": link}

    if service != "TraceMoe":
        res = await ctx.bot.d.aio_session.get(
            "https://saucenao.com/search.php?", params=params
        )
        if res.ok:
            res = await res.json()

            if res["header"]["status"] < 0:
                logger.error(f"SauceNAO error: {res['header']['message']}")
                await ctx.edit_last_response(f"SauceNAO error (status {res['header']['status']})")
                return

            data = res["results"][0]
            try:
                embed, view = await _complex_parsing(ctx, data)
                if float(data["header"]["similarity"]) < 60.0:
                    disp_embed = hk.Embed(
                        title="Possible false match",
                        description=(
                            "We might have encountered a false match."
                            "\n\nFalse matches often contain NSFW matches or "
                            "in rarer cases, what you're actually looking for."
                            "\nPlease use the ❌ or Go Back button should that happen."
                        ),
                        color=colors.WARN,
                        timestamp=datetime.now().astimezone(),
                    )
                    view = AuthorView(user_id=ctx.author.id)
                    view.add_item(
                        SwapButton(
                            label1="Show anyway",
                            label2="Go Back",
                            emoji1=hk.Emoji.parse("<:next:1136984292921200650>"),
                            emoji2=hk.Emoji.parse("<:previous:1136984315415236648>"),
                            original_page=disp_embed,
                            swap_page=embed,
                        )
                    )
                    # url["url"] = url["url"].split("?")[0]
                    view.add_item(
                        GenericButton(
                            url=f"https://yandex.com/images/search?url={quote(url['url'])}&rpt=imageview",
                            label="Search Yandex",
                        )
                    )
                    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                    choice = await ctx.edit_last_response(
                        content=None, embed=disp_embed, components=view
                    )
                    await view.start(choice)
                    await view.wait()

                else:
                    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                    view.clean_items = False
                    choice = await ctx.edit_last_response(
                        content=None, embed=embed, components=view
                    )
                    await view.start(choice)
                    await view.wait()

            except Exception:
                logger.error(f"Sauce parser failed, json returned: {res}")
                embed, view = await _simple_parsing(ctx, data)
                view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                view.clean_items = False
                choice = await ctx.edit_last_response(
                    content=None, embed=embed, components=view
                )
                await view.start(choice)
                await view.wait()
        else:
            await ctx.edit_last_response(f"Ran into en error, `code : {res.status}`")

    else:
        try:
            async with ctx.bot.d.aio_session.get(
                "https://api.trace.moe/search", params={"url": link}
            ) as res:
                if res.ok:
                    res = (await res.json())["result"]
                    raw_filename = res[0]["filename"]
                    raw_filename = raw_filename.replace(".mkv", "").replace(".mp4", "")
                    sauce = re.sub(
                        r"\[.*?\]", "", re.sub(r"\(.*?\)", "", raw_filename)
                    ).strip()
                    sauce += f" [Clip]({res[0].get('video')})"

                    view = AuthorView(user_id=ctx.author.id, timeout=15 * 60)
                    view.add_item(
                        GenericButton(
                            style=hk.ButtonStyle.LINK,
                            emoji=hk.Emoji.parse(emotes.AL.value),
                            url=f"https://anilist.co/anime/{res[0]['anilist']}",
                        )
                    )
                    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))

                    choice = await ctx.edit_last_response(
                        content=None,
                        embed=hk.Embed(color=0x000000)
                        .add_field(
                            "Similarity", f"{round(res[0]['similarity']*100, 2)}"
                        )
                        .add_field("Source", sauce)
                        .add_field("Episode", res[0]["episode"] or "1", inline=True)
                        .add_field(
                            "Timestamp",
                            (
                                f"{int(res[0]['from']//60)}:{int(res[0]['from']%60)} -"
                                f" {int(res[0]['to']//60)}:{int(res[0]['to']%60)}"
                                f""
                            ),
                            inline=True,
                        )
                        .set_thumbnail(res[0]["image"])
                        .set_author(name="Search results returned the follows: ")
                        .set_footer(
                            text="Powered by: Trace.Moe",
                        ),
                        components=view,
                    )
                    await view.start(choice)
                    await view.wait()
                else:
                    await ctx.respond("Couldn't find it.")
        except Exception:
            logger.error(f"Sauce parser failed, json returned: {res}")
            await ctx.respond("Ran into an unknown exception")


async def _complex_parsing(ctx: lb.Context, data: dict):
    """A usually stable method to form an embed via sauce results"""
    sauce = "😵"

    view = AuthorView(user_id=ctx.author.id, timeout=15 * 60)

    if "MangaDex" in data["header"]["index_name"]:
        try:
            if "mal_id" in data["data"].keys():
                view.add_item(
                    GenericButton(
                        style=hk.ButtonStyle.LINK,
                        emoji=hk.Emoji.parse(emotes.AL.value),
                        url=(await al_from_mal(data["data"]["mal_id"])),
                    )
                )
            else:
                view.add_item(
                    GenericButton(
                        style=hk.ButtonStyle.LINK,
                        emoji=hk.Emoji.parse(emotes.AL.value),
                        url=(await al_from_mal(name=data["data"]["source"])),
                    )
                )
        except Exception:
            pass

        view.add_item(
            GenericButton(
                style=hk.ButtonStyle.LINK,
                emoji=emotes.MANGADEX.value,
                # emoji=hk.Emoji.parse("<:mangadex:1128015134426677318>"),
                url=data["data"]["ext_urls"][0],
            )
        )
        return (
            hk.Embed(
                color=0x000000,
            )
            .add_field("Similarity", data["header"]["similarity"])
            .add_field("Source", f"{data['data']['source']} {data['data']['part']}")
            .add_field("Author", data["data"]["author"])
            .set_thumbnail(data["header"]["thumbnail"])
            .set_author(name="Search results returned the follows: ")
            .set_footer(
                text="Powered by: SauceNAO",
                icon="https://i.imgur.com/2VRIEPR.png",
            ),
            view,
        )

    elif "Anime" in data["header"]["index_name"]:
        if len(data["data"]["ext_urls"]) > 1:
            view.add_item(
                GenericButton(
                    style=hk.ButtonStyle.LINK,
                    emoji=hk.Emoji.parse(emotes.AL.value),
                    url=data["data"]["ext_urls"][2],
                )
            )
        else:
            try:
                params = {
                    "source": "anidb",
                    "id": data["data"]["ext_urls"][0].split("/")[-1],
                    "include": "anilist",
                }
                res = await ctx.bot.d.aio_session.get(
                    "https://arm.haglund.dev/api/v2/ids", params=params
                )

                if res.ok:
                    res = await res.json()

                    view.add_item(
                        GenericButton(
                            style=hk.ButtonStyle.LINK,
                            emoji=hk.Emoji.parse(emotes.AL.value),
                            url=f"https://anilist.co/anime/{res['anilist']}",
                        )
                    )
                else:
                    await ctx.respond("not ok ")

            except Exception:
                pass

        return (
            hk.Embed(
                color=0x000000,
            )
            .add_field("Similarity", data["header"]["similarity"])
            .add_field(
                "Source",
                data["data"]["source"],
            )
            .add_field("Episode", data["data"]["part"], inline=True)
            .add_field("Timestamp", data["data"]["est_time"], inline=True)
            .set_thumbnail(data["header"]["thumbnail"])
            .set_author(name="Search results returned the follows: ")
            .set_footer(
                text="Powered by: SauceNAO",
                icon="https://i.imgur.com/2VRIEPR.png",
            ),
            view,
        )

    elif "Danbooru" in data["header"]["index_name"]:
        view.add_item(
            GenericButton(
                style=hk.ButtonStyle.LINK,
                emoji=hk.Emoji.parse(emotes.DANBOORU.value),
                url=data["data"]["ext_urls"][0],
            )
        )
        view.add_item(
            GenericButton(
                style=hk.ButtonStyle.LINK,
                label="Original Image",
                url=data["data"]["source"],
            )
        )
        creator = ""
        if isinstance(data["data"]["creator"], str):
            creator = data["data"]["creator"]
        else:
            creator = ", ".join(data["data"]["creator"])
        return (
            hk.Embed(
                color=0x000000,
            )
            .add_field("Similarity", data["header"]["similarity"])
            .add_field("Artist", creator, inline=True)
            .add_field("Character(s)", data["data"]["characters"], inline=True)
            .add_field("Source Material", data["data"]["material"])
            .set_thumbnail(data["header"]["thumbnail"])
            .set_author(name="Search results returned the follows: ")
            .set_footer(
                text="Powered by: SauceNAO",
                icon="https://i.imgur.com/2VRIEPR.png",
            ),
            view,
        )

    elif "Pixiv" in data["header"]["index_name"]:
        view.add_item(
            GenericButton(
                style=hk.ButtonStyle.LINK,
                emoji=hk.Emoji.parse(emotes.PIXIV.value),
                url=data["data"]["ext_urls"][0],
            )
        )
        return (
            hk.Embed(
                color=0x000000,
            )
            .add_field("Similarity", data["header"]["similarity"])
            .add_field(
                "Author",
                f"[{data['data']['member_name']}](https://www.pixiv.net/en/users/{data['data']['member_id']})",
            )
            .add_field("Title", data["data"]["title"])
            .set_thumbnail(data["header"]["thumbnail"])
            .set_author(name="Search results returned the follows: ")
            .set_footer(
                text="Powered by: SauceNAO",
                icon="https://i.imgur.com/2VRIEPR.png",
            ),
            view,
        )

    elif "H-Misc (E-Hentai)" in data["header"]["index_name"]:
        view.add_item(
            GenericButton(
                style=hk.ButtonStyle.LINK,
                emoji=hk.Emoji.parse(emotes.VNDB.value),
                label="VNDB",
                url=await vndb_url(data["data"]["source"]),
            )
        )

        return (
            hk.Embed(
                color=0x000000,
            )
            .add_field("Similarity", data["header"]["similarity"])
            .add_field("Source", data["data"]["source"])
            .add_field("Creator", ", ".join(data["data"]["creator"]))
            .set_thumbnail(data["header"]["thumbnail"])
            .set_author(name="Search results returned the follows: ")
            .set_footer(
                text="Powered by: SauceNAO",
                icon="https://i.imgur.com/2VRIEPR.png",
            ),
            view,
        )

    else:
        sauce = "😵"
        if "source" in data["data"].keys() and data["data"]["source"] != "":
            if "ext_urls" in data["data"].keys():
                if not (
                    check_if_url(data["data"]["source"])
                    and check_if_url(data["data"]["ext_urls"][0])
                ):
                    sauce = f"[{data['data']['source']}]({data['data']['ext_urls'][0]})"
                else:
                    sauce = (
                        f"Link1: {data['data']['source']} "
                        f"\nLink2: {data['data']['ext_urls'][0]}"
                    )
            else:
                sauce = data["data"]["source"]
        else:
            sauce = data["data"]["ext_urls"][0]

        embed = (
            hk.Embed(color=0x000000)
            .add_field("Similarity", data["header"]["similarity"])
            .add_field("Source", sauce)
            .set_thumbnail(data["header"]["thumbnail"])
            .set_author(name="Search results returned the follows: ")
            .set_footer(
                text="Powered by: SauceNAO", icon="https://i.imgur.com/2VRIEPR.png"
            )
        )

        for i, item in enumerate(data["data"].keys()):
            if item not in ["source", "ext_urls"] and "id" not in item:
                if item in ["created_at", "published", "published_at"]:
                    data["data"][item] = f"<t:{iso_to_timestamp(data['data'][item])}:D>"

                if item == "creator":
                    if not isinstance(data["data"]["creator"], str):
                        data["data"]["creator"] = ", ".join(data["data"]["creator"])

                if i % 3:
                    embed.add_field(
                        sanitize_field(item), data["data"][item], inline=True
                    )
                else:
                    embed.add_field(sanitize_field(item), data["data"][item])

        return (embed, view)


async def _simple_parsing(ctx: lb.Context, data: dict):
    """A mostly stable method to form an embed via sauce results"""
    sauce = "😵"
    if "source" in data["data"].keys():
        if "ext_urls" in data["data"].keys():
            sauce = f"[{data['data']['source']}]({data['data']['ext_urls'][0]})"
        else:
            sauce = data["data"]["source"]
    else:
        sauce = data["data"]["ext_urls"][0]
    return (
        hk.Embed(color=0x000000)
        .add_field("Similarity", data["header"]["similarity"])
        .add_field("Source", sauce)
        .set_thumbnail(data["header"]["thumbnail"])
        .set_author(name="Search results returned the follows: ")
        .set_footer(
            text="Powered by: SauceNAO", icon="https://i.imgur.com/2VRIEPR.png"
        ),
        AuthorView(user_id=ctx.author.id),
    )


def sanitize_field(name: str) -> str:
    """Replacing _ with space"""
    return name.replace("_", " ").capitalize()


async def al_from_mal(
    mal_id: t.Optional[int] = None,
    type: t.Optional[str] = None,
    name: t.Optional[str] = None,
) -> t.Optional[str]:
    """Anilist URL from MAL id"""
    return await ALManga.al_url_from_mal(
        sauce_plugin.bot.d.anilist, mal_id=mal_id, name=name
    )


async def vndb_url(text: str) -> t.Union[str, None]:
    """Gives the vndb url of a query object

    Args:
        text (str): Query

    Returns:
        str: The url
    """
    pattern = r"\[.*?\]"
    result_text = re.sub(pattern, "", text)

    url = "https://api.vndb.org/kana/vn"
    headers = {"Content-Type": "application/json"}
    data = {
        "filters": ["search", "=", result_text],
        "fields": "title",
        # "sort": "title"
    }
    req = await sauce_plugin.bot.d.aio_session.post(url, headers=headers, json=data)

    if not req.ok:
        return

    req = await req.json()
    return f"https://vndb.org/{req['results'][0]['id']}"


pattern = r"https?://\S+|www\.\S+"

url_regex = re.compile(pattern)


class MyModal(miru.Modal):
    # Define our modal items
    # You can also use Modal.add_item() to add items to the modal after instantiation, just like with views.
    num = miru.TextInput(
        label="Which image to search for?",
        placeholder="The attachment number to consider",
        required=True,
    )

    # The callback function is called after the user hits 'Submit'
    async def callback(self, ctx: miru.ModalContext) -> None:
        ...

    #     # You can also access the values using ctx.values, Modal.values, or use ctx.get_value_by_id()


async def _find_the_url(ctx) -> dict:
    """A function which finds the link (if it exists) across contexts

    Args:
        ctx (:obj:`lb.Context`): The context (user, message or slash)

    Returns:
        dict: {
            "url" : The link (if applicable)
            "errorMessage": If applicable otherwise None
        }
    """
    if isinstance(ctx, lb.UserContext):
        return {"url": ctx.options.target.display_avatar_url.url, "errorMessage": None}

    elif isinstance(ctx, lb.SlashContext):
        url = ctx.raw_options["link"]

        if not check_if_url(url):
            msg = f"There's no valid url in this message {emotes.SIP.value}"
            return {
                "url": None,
                "errorMessage": msg,
            }
        try:
            if _is_tenor_link(url):
                # If the tenor scrapping fails, then it sends the original link back
                link = await tenor_link_from_gif(url, ctx.bot.d.aio_session)
                if link == url:
                    return {
                        "url": None,
                        "errorMessage": "Unknown error fetching tenor url",
                    }
                return {"url": link, "errorMessage": None}

            error = await _check_media(url, None, ctx.bot.d.aio_session)
            return {"url": url, "errorMessage": error}
        except Exception as e:
            logger.error("Error while trying to find img url", exc_info=True)
            return {"url": None, "errorMessage": f"Exception: {type(e).__name__}"}

    elif isinstance(ctx, lb.MessageContext):
        candidates = _collect_candidates(ctx.options["target"])

        if not candidates:
            msg = f"There's nothing here to find the sauce of {emotes.SIP.value}"
            return ctx, {"url": None, "errorMessage": msg}

        if len(candidates) == 1:
            candidate = candidates[0]
            await ctx.respond(hk.ResponseType.DEFERRED_MESSAGE_CREATE)
        else:
            candidate = await _pick_candidate(ctx, candidates)
            if not candidate:
                return ctx, {"url": None, "errorMessage": None}

        try:
            error = await _check_media(
                candidate["url"], candidate["size"], ctx.bot.d.aio_session
            )
            if error:
                return ctx, {"url": None, "errorMessage": error}

            if not candidate["is_video"]:
                return ctx, {"url": candidate["url"], "errorMessage": None}

            video, download_error = await _download_video(candidate["url"])
            if download_error:
                msg = f"Failed to download video ({download_error})"
                return ctx, {"url": None, "errorMessage": msg}

            try:
                frame = await asyncio.to_thread(_frame_at_quarter, video)
            except Exception:
                frame = None
            if not frame:
                return ctx, {"url": None, "errorMessage": "Failed to process video"}

            # SauceNAO needs a link, so the frame is attached to the message to get one
            frame_message = await ctx.interaction.edit_initial_response(
                attachment=hk.Bytes(frame, "frame.jpg")
            )
            return ctx, {"url": frame_message.attachments[0].url, "errorMessage": None}
        except Exception:
            logger.error("Error while trying to find img url", exc_info=True)
            return ctx, {"url": None, "errorMessage": "Unknown Error"}

    return {
        "url": None,
        "errorMessage": "You're prolly trying to use a prefix context (not implemented)",
    }


def _collect_candidates(message: hk.Message) -> list[dict]:
    """Gather the searchable images/videos of a message: attachments, embeds and bare links"""
    candidates = []

    for attachment in message.attachments:
        media_type = (attachment.media_type or "").split(";")[0]
        is_video = media_type.startswith("video/")
        if media_type in IMAGE_TYPES or is_video:
            candidates.append(
                {
                    "emoji": "🎞️" if is_video else "🖼️",
                    "label": f"{'Video' if is_video else 'Attachment'} · {attachment.filename}",
                    "description": f"{attachment.size / (1024 * 1024):.1f} MB",
                    "url": attachment.url,
                    "is_video": is_video,
                    "size": attachment.size,
                }
            )

    # Embeds already carry the media url (incl. tenor/klipy gifs), via Discord's proxy.
    # Embed videos (e.g. tweets) use their thumbnail rather than being downloaded
    media_embeds = [embed for embed in message.embeds if embed.image or embed.thumbnail]
    image_counts = Counter(embed.url for embed in media_embeds)
    image_positions = Counter()
    embed_labels = {}

    for embed in media_embeds:
        media = embed.image or embed.thumbnail

        # Extra images of a multi-image post come as bare embeds sharing the first one's url
        if embed.url not in embed_labels:
            embed_labels[embed.url] = _embed_label(embed)
        emoji, label = embed_labels[embed.url]

        image_positions[embed.url] += 1
        if image_counts[embed.url] > 1:
            label = f"{label} · {image_positions[embed.url]}/{image_counts[embed.url]}"

        candidates.append(
            {
                "emoji": emoji,
                "label": label,
                "description": urlparse(media.url).hostname,
                "url": media.proxy_url or media.url,
                "is_video": False,
                "size": None,
            }
        )

    embed_links = {embed.url for embed in message.embeds}
    for link in url_regex.findall(message.content or ""):
        link = link.rstrip(">")
        if link not in embed_links:
            candidates.append(
                {
                    "emoji": "🔗",
                    "label": f"Link · {urlparse(link).hostname or link}",
                    "description": None,
                    "url": link,
                    "is_video": False,
                    "size": None,
                }
            )

    return candidates


def _embed_label(embed: hk.Embed) -> tuple[str, str]:
    """Icon and short dropdown label for an embed (GIF, tweet or anything else)"""
    provider = embed.provider.name if embed.provider else None
    host = (urlparse(embed.url or "").hostname or "").removeprefix("www.")
    title = (embed.title or "").split(" - ")[0].removesuffix(" GIF")

    if provider in GIF_PROVIDERS:
        return "🎞️", f"{provider} GIF · {title}"

    if host in TWITTER_HOSTS:
        author = embed.author.name if embed.author and embed.author.name else ""
        handle = re.search(r"\(@(\w+)\)", author)
        name = f"@{handle.group(1)}" if handle else author or host
        return "🐦", f"Tweet{' video' if embed.video else ''} · {name}"

    if embed.video:
        return "🎞️", f"Video · {title or provider or host}"
    return "🖼️", f"{provider or host} · {title or 'Embed'}"


class CandidateSelect(miru.TextSelect):
    """Dropdown to choose which image/video of a message to search"""

    async def callback(self, ctx: miru.ViewContext) -> None:
        self.view.answer = int(self.values[0])
        label = self.options[self.view.answer].label
        await ctx.edit_response(content=f"Searching **{label}**", components=[])
        self.view.stop()


async def _pick_candidate(
    ctx: lb.MessageContext, candidates: list[dict]
) -> t.Optional[dict]:
    """Ask the user which candidate to search"""
    options = [
        miru.SelectOption(
            label=candidate["label"][:100],
            value=str(index),
            description=(candidate["description"] or "")[:100] or None,
            emoji=candidate["emoji"],
        )
        for index, candidate in enumerate(candidates[:25])  # Discord's dropdown limit
    ]

    view = AuthorView(user_id=ctx.author.id, timeout=60, clean_items=False)
    view.add_item(CandidateSelect(options=options, placeholder="Pick one"))

    response = await ctx.respond(
        "Which image/video to find the source for?", components=view
    )
    await view.start(response)
    await view.wait()

    if view.answer is None:
        await ctx.edit_last_response("Timed out", components=[])
        return None
    return candidates[view.answer]


async def _check_media(
    link: str, size: t.Optional[int], session
) -> t.Optional[str]:
    """Check a link is valid, from a trusted site, an image (when size is unknown) and within 100MB

    Returns:
        t.Optional[str]: The error message, None if all checks pass
    """
    if not check_if_url(link):
        return f"There's no valid url in this message {emotes.SIP.value}"

    if not check_if_known_emoji_provider(link):
        return f"Site {urlparse(link).hostname} is not trusted ⚠️"

    if size is None:
        media_type, size = await _fetch_media_headers(link, session)
        if media_type not in IMAGE_TYPES:
            return f"Please enter a valid image link {emotes.SMILE.value}"

    # Unknown size is allowed through
    if size and size > MAX_MEDIA_SIZE:
        return "Files over 100MB are not supported"
    return None


async def _fetch_media_headers(link: str, session) -> tuple[str, t.Optional[int]]:
    """HEAD a link for its content type and size (None if not reported)"""
    try:
        # encoded=True keeps signed links (e.g. Discord's proxy) from being re-encoded
        async with session.head(yarl.URL(link, encoded=True)) as response:
            media_type = response.headers.get("content-type", "").split(";")[0]
            return media_type, response.content_length
    except Exception:
        return "", None


async def _download_video(
    link: str,
) -> tuple[t.Optional[io.BytesIO], t.Optional[str]]:
    """Download a video into memory, abandoning it once it crosses 100MB

    Returns:
        tuple: (video, None) on success, otherwise (None, reason)
    """
    try:
        # Plain session as the cached one reads and stores the whole body before returning
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120)
        ) as session:
            async with session.get(yarl.URL(link, encoded=True)) as response:
                if not response.ok:
                    return None, f"error: HTTP {response.status}"

                video = io.BytesIO()
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    video.write(chunk)
                    if video.tell() > MAX_MEDIA_SIZE:
                        return None, "over 100MB"
    except Exception as e:
        return None, f"error: {type(e).__name__}"

    video.seek(0)
    return video, None


def _frame_at_quarter(video: io.BytesIO) -> t.Optional[bytes]:
    """Grab the frame at 25% of the video's length as JPEG bytes"""
    with av.open(video) as container:
        stream = container.streams.video[0]
        target = (container.duration or 0) / av.time_base * 0.25
        container.seek(int(target / stream.time_base), stream=stream)

        for frame in container.decode(stream):
            if (frame.time or 0) >= target:
                output = io.BytesIO()
                frame.to_image().save(output, format="JPEG", quality=90)
                return output.getvalue()
    return None


def _is_tenor_link(link) -> bool:
    """Check if a link is a tenor gif page"""
    parsed = urlparse(link)
    return parsed.hostname in ("tenor.com", "www.tenor.com") and parsed.path.startswith("/view")


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(sauce_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(sauce_plugin)
