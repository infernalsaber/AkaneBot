"""Search the source of a given image"""


import os
import re
import traceback
import typing as t
from datetime import datetime
from urllib.parse import quote

import dotenv
import hikari as hk
import lightbulb as lb
import miru
from miru.ext import nav

from functions.buttons import (
    GenericButton,
    KillButton,
    KillNavButton,
    NavButton,
    SwapButton,
    SwapNaviButton
)
from functions.checks import trusted_user_check
from functions.models import ColorPalette as colors
from functions.models import EmoteCollection as emotes
from functions.utils import (
    check_if_url,
    dlogger,
    get_random_quote,
    is_image,
    iso_to_timestamp,
    poor_mans_proxy,
    tenor_link_from_gif
)
from functions.views import AuthorNavi, AuthorView

dotenv.load_dotenv()

SAUCENAO_KEY = os.getenv("SAUCENAO_KEY")

sauce_plugin = lb.Plugin(
    "Sauce", "Finding the source of an image", include_datastore=True
)
sauce_plugin.d.help_image = "https://i.imgur.com/YxvyvaF.png"
sauce_plugin.d.help_emoji = "❓"
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
                await ctx.respond(f"Error: {res['header']['message']}")
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
                await dlogger(
                    ctx.bot, f"Sauce parser failed, json returned: ```{res}```"
                )

        else:
            await ctx.respond(f"Ran into en error, `code : {res.status}`")


@sauce_plugin.command
@lb.set_max_concurrency(1, lb.GlobalBucket)
@lb.add_checks(trusted_user_check)
@lb.add_cooldown(length=86400, uses=10, bucket=lb.UserBucket)
@lb.add_cooldown(length=86400, uses=20, bucket=lb.GuildBucket)
@lb.command("Video Sauce", "Search the sauce of video", auto_defer=True)
@lb.implements(lb.MessageCommand)
async def find_video_sacue(ctx: lb.MessageContext):
    """Find the sauce of a video

    Args:
        ctx (lb.MessageContext): The context the command is invoked in
    """

    if ctx.options["target"].attachments:
        vid_url = ctx.options["target"].attachments[0].url

    print("Video URL: ", vid_url)

    vid_bytes = await poor_mans_proxy(vid_url, ctx.bot.d.aio_session)

    print("Video Bytes")

    # To save the bytes to memory
    with open("temp.mp4", "wb") as f:
        f.write(vid_bytes.read())

    print("Written to filesystem")

    os.system("ffmpeg -i temp.mp4 -vf fps=1 temp.jpg")

    print("Converted to image")

    msg = await ctx.respond(attachments=["temp.jpg"])
    message = await msg.message()
    link = message.attachments[0].url

    # await msg.delete()

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
                await ctx.edit_last_response(f"Error: {res['header']['message']}")
                return

            try:
                embed, view = await _complex_parsing(ctx, res["results"][0])

                if float(res["results"][0]["header"]["similarity"]) < 60.0:
                    await msg.delete()
                    view = AuthorNavi(
                        pages=[
                            nav.Page(
                                content=ctx.options.target.make_link(ctx.guild_id),
                                embed=hk.Embed(
                                    title="Possible false match",
                                    description=(
                                        "We might have encountered a false match."
                                        "\n\nFalse matches often contain NSFW matches or "
                                        "in rarer cases, what you're actually looking for."
                                        "\nPlease use the ❌ or Go Back button should that happen."
                                    ),
                                    color=colors.WARN,
                                    timestamp=datetime.now().astimezone(),
                                ),
                            ),
                            nav.Page(
                                content=ctx.options.target.make_link(ctx.guild_id),
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
                                url=f"https://yandex.com/images/search?url={quote(link)}&rpt=imageview",
                                label="Search Yandex",
                            ),
                            KillNavButton(style=hk.ButtonStyle.SECONDARY),
                        ],
                        user_id=ctx.author.id,
                    )
                    await view.send(ctx.interaction, responded=True)

                else:
                    # view.
                    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                    view.clean_items = False

                    choice = await ctx.edit_last_response(
                        content=ctx.options.target.make_link(ctx.guild_id),
                        embed=embed,
                        components=view,
                        attachments=None,
                    )

                    await view.start(choice)
                    await view.wait()
            except Exception as e:
                await dlogger(
                    ctx.bot, f"Sauce parser failed, json returned: ```{res}```"
                )
                embed, view = await _simple_parsing(ctx, res["results"][0])
                view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                view.clean_items = False
                choice = await ctx.edit_last_response(
                    embed=embed, components=view, attachments=None
                )
                await ctx.respond(e)
                await view.start(choice)
                await view.wait()
        else:
            await ctx.respond(f"Ran into en error, `code : {res.status}`")

    os.remove("temp.mp4")
    os.remove("temp.jpg")

    # ctx.get_channel()


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
    else:
        await ctx.respond(url["errorMessage"])
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
                await ctx.respond(f"Error: {res['header']['message']}")
                return

            try:
                embed, view = await _complex_parsing(ctx, res["results"][0])

                if float(res["results"][0]["header"]["similarity"]) < 60.0:
                    view = AuthorNavi(
                        pages=[
                            nav.Page(
                                content=message_link,
                                embed=hk.Embed(
                                    title="Possible false match",
                                    description=(
                                        "We might have encountered a false match."
                                        "\n\nFalse matches often contain NSFW matches or "
                                        "in rarer cases, what you're actually looking for."
                                        "\nPlease use the ❌ or Go Back button should that happen."
                                    ),
                                    color=colors.WARN,
                                    timestamp=datetime.now().astimezone(),
                                ),
                            ),
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
                    await view.send(ctx, responded=True)

                else:
                    view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                    view.clean_items = False
                    choice = await ctx.respond(
                        content=message_link,
                        embed=embed,
                        components=view,
                    )
                    await view.start(choice)
                    await view.wait()
            except Exception as e:
                await dlogger(
                    ctx.bot, f"Sauce parser failed, json returned: ```{res}```"
                )
                embed, view = await _simple_parsing(ctx, res["results"][0])
                view.add_item(KillButton(style=hk.ButtonStyle.SECONDARY, label="❌"))
                choice = await ctx.respond(embed=embed, components=view)
                await ctx.respond(e)
                await view.start(choice)
                await view.wait()
        else:
            await ctx.respond(f"Ran into en error, `code : {res.status}`")


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
                await ctx.edit_last_response(f"Error: {res['header']['message']}")
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
                await dlogger(
                    ctx.bot, f"Sauce parser failed, json returned: ```{res}```"
                )
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
            await dlogger(ctx.bot, f"Sauce parser failed, json returned: ```{res}```")
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
) -> str:
    """Anilist URL from MAL id"""
    query = """
  query ($mal_id: Int, $search: String) { # Define which variables will be used (id)
    Media (idMal: $mal_id, search: $search, type: MANGA) {
      siteUrl
    }
  }

  """

    variables = {"mal_id": mal_id, "search": name}
    return (
        await (
            await sauce_plugin.bot.d.aio_session.post(
                "https://graphql.anilist.co",
                json={"query": query, "variables": variables},
            )
        ).json()
    )["data"]["Media"]["siteUrl"]


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

            if not await is_image(url, ctx.bot.d.aio_session):
                msg = f"Please enter a valid image link {emotes.SMILE.value}"
                return {
                    "url": url,
                    "errorMessage": msg,
                }

            return {"url": url, "errorMessage": None}
        except Exception as e:
            return {"url": None, "errorMessage": f"Exception: ```{e}```"}

    elif isinstance(ctx, lb.MessageContext):
        url = None
        errorMessage = "No valid url found"

        message = ctx.options["target"]

        if message.content:
            match = url_regex.search(message.content)
            if match:
                url = match.group()

        if url:
            if await is_image(url, ctx.bot.d.aio_session):
                return ctx, {"url": url, "errorMessage": None}

            if _is_tenor_link(url):
                link = await tenor_link_from_gif(url, ctx.bot.d.aio_session)
                if link == url:
                    return ctx, {
                        "url": url,
                        "errorMessage": "Unknown error fetching tenor url",
                    }
                return ctx, {"url": link, "errorMessage": None}

        if not message.attachments:
            msg = f"There's nothing here to find the sauce of {emotes.SIP.value}"
            return ctx, {
                "url": None,
                "errorMessage": msg,
            }

        if len(message.attachments) > 1:
            # Temp disable due to modal/api issues
            # test = MyModal(title="Sauce Search Image Selection", timeout=60)
            # await test.send(ctx)
            # await test.wait(timeout=60)
            # if test.last_context is None:
            #     return
            # ctx = test.last_context
            
            
            # val = test.num.value
            val = "1"
            await ctx.respond(hk.ResponseType.DEFERRED_MESSAGE_CREATE)
        else:
            val = "1"
            await ctx.respond(hk.ResponseType.DEFERRED_MESSAGE_CREATE)

        try:
            if not isinstance(eval(val), int):
                return

            val = int(val)

            if val > len(message.attachments) + 1 or val < 1:
                return ctx, {
                    "url": None,
                    "errorMessage": "Invalid attachment number",
                }

            if await is_image(message.attachments[val - 1].url, ctx.bot.d.aio_session):
                return ctx, {
                    "url": message.attachments[val - 1].url,
                    "errorMessage": None,
                }
            return ctx, {"url": url, "errorMessage": errorMessage}
        except Exception:
            await dlogger(
                ctx.bot,
                f"Error while trying to find img url: ```{traceback.format_exc()}```",
            )
            await ctx.respond("Unknown Error")

    return {
        "url": None,
        "errorMessage": "You're prolly trying to use a prefix context (not implemented)",
    }


def _is_tenor_link(link) -> bool:
    """Very barebones way to check if a confirmed link is a tenor gif"""
    if "//tenor.com/view" in link:
        return True
    return False


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(sauce_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(sauce_plugin)
