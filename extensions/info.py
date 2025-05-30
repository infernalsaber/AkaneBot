"""Get information about a role, server, user, bot etc."""
import io
import json
import typing as t
from datetime import datetime
from math import floor
from subprocess import PIPE, Popen

import hikari as hk
import lightbulb as lb
import pandas as pd
import psutil
import seventv
from miru.ext import nav
from PIL import Image, ImageOps
from rapidfuzz import process
from rapidfuzz.utils import default_process

from functions.buttons import (
    AddEmoteButton,
    CustomNextButton,
    CustomPrevButton,
    KillNavButton,
    SwapButton,
)
from functions.models import ColorPalette as colors
from functions.utils import is_image
from functions.views import AuthorNavi, AuthorView

info_plugin = lb.Plugin("Utility", "Utility and info commands", include_datastore=True)
info_plugin.d.help = True
info_plugin.d.help_emoji = "⚙️"
info_plugin.d.help_image = "https://i.imgur.com/nsg3lZJ.png"


def search_sneedex(search_str, threshold=80):
    # Read the table
    df = pd.read_html("https://static.sneedex.moe/")[0]

    # Get matches from title column
    title_matches = process.extract(
        search_str,
        df["Title"],
        limit=1,
        score_cutoff=threshold,
        processor=lambda x: x.lower(),
    )

    # Get matches from alias column
    alias_matches = process.extract(
        search_str,
        df["Alias"],
        limit=1,
        score_cutoff=threshold,
        processor=lambda x: x.lower(),
    )

    # Combine matches and get the best one
    all_matches = title_matches + alias_matches
    if not all_matches:
        return json.dumps({"error": "No matches found above threshold"})

    best_match = max(all_matches, key=lambda x: x[1])
    match_idx = (
        df[df["Title"] == best_match[0]].index[0]
        if best_match[0] in df["Title"].values
        else df[df["Alias"] == best_match[0]].index[0]
    )

    # Return relevant columns as JSON
    result = {
        "title": df.iloc[match_idx]["Title"],
        "best": df.iloc[match_idx]["Best"],
        "alt": df.iloc[match_idx]["Alt"],
        "notes": df.iloc[match_idx]["Notes"],
        "comps": df.iloc[match_idx]["Comps"],
        "updated": df.iloc[match_idx]["Updated"],
    }

    return result


@info_plugin.command
@lb.add_checks(lb.guild_only)
@lb.option(
    "series", "The series to search for", modifier=lb.OptionModifier.CONSUME_REST
)
@lb.command(
    "sneedex",
    "Search for a series' releases on sneedex",
    aliases=["sd", "release"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand)
async def sneedex_cmd(ctx: lb.Context, series: str) -> None:
    """Search for a series' releases on sneedex

    Args:
        ctx (lb.Context): Context for the command
        series (str): The series to search for
    """

    try:
        series_data = search_sneedex(series)
        await ctx.respond(
            hk.Embed(title=series_data["title"], color=0x0991CF)
            .add_field("Best Release", series_data["best"])
            .add_field("Alt", series_data["alt"])
            .set_footer("Via: sneedex.moe")
        )
    except Exception as e:
        await ctx.respond(f"Can't fetch the release for `{series}` right now {e}")


@info_plugin.command
@lb.add_checks(lb.guild_only)
@lb.option("role", "The role", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command("inrole", "List of users in role", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def inrole_cmd(ctx: lb.Context, role: str) -> None:
    """List of members in a role or interested in an event

    Args:
        ctx (lb.Context): Context for the command
        role (str): The role/event
    """

    # Trying to convert it into an int (hk.SnowFlake) basically, if possible
    try:
        role = int(role)
    except ValueError:
        pass

    if not isinstance(role, hk.Role):
        if isinstance(role, int):
            for role_ in ctx.bot.cache.get_roles_view_for_guild(ctx.guild_id).values():
                if role == role_.id:
                    role = role_
                    break
            else:
                await ctx.respond("No matching roles found")
                return

        elif role[0] == "<":
            for role_ in ctx.bot.cache.get_roles_view_for_guild(ctx.guild_id).values():
                if role == role_.mention:
                    role = role_
                    break
            else:
                await ctx.respond("No matching roles found")
                return
        else:
            guild_roles = {
                role_.name: role_
                for role_ in ctx.bot.cache.get_roles_view_for_guild(
                    ctx.guild_id
                ).values()
            }

            ans = process.extractOne(
                role,
                list(guild_roles.keys()),
                score_cutoff=85,
                processor=default_process,
            )

            # Unpacking the closest value, if it exists
            if ans:
                closest_role_match, *_ = ans

                role = guild_roles[closest_role_match]
            else:
                await ctx.respond("No matching roles found")
                return

    try:
        d1, d2 = "", ""

        counter: int = 0

        pages = []

        for member in ctx.bot.cache.get_members_view_for_guild(ctx.guild_id).values():
            if role.id in member.role_ids:
                d1 += f"{member.id: <20}\n"
                username = member.username.replace("_", r"\_")
                d2 += f"{username}\n"
                counter += 1

        if not counter:
            await ctx.respond(
                hk.Embed(
                    title=f"List of users in {role.name} role ({counter})",
                    timestamp=datetime.now().astimezone(),
                    color=role.color or 0xFFFFFF,
                ).set_thumbnail(role.icon_url)
            )

            return

        mem_ids = [
            d1.split("\n")[i : i + 20] for i in range(0, len(d1.split("\n")), 20)
        ]
        mem_names = [
            d2.split("\n")[i : i + 20] for i in range(0, len(d2.split("\n")), 20)
        ]

        for i, item in enumerate(mem_ids):
            pages.append(
                hk.Embed(
                    title=f"List of users in {role.name} role ({counter})",
                    timestamp=datetime.now().astimezone(),
                    color=role.color or 0xFFFFFF,
                )
                .set_thumbnail(role.icon_url)
                .add_field("UID", "\n".join(item), inline=True)
                .add_field("Name", "\n".join(mem_names[i]), inline=True)
            )

        if len(pages) == 1:
            await ctx.respond(pages[0])
            return

        view = AuthorNavi(pages=pages, user_id=ctx.author.id, buttons="default")

        await view.send(ctx.channel_id)
        return
    except Exception as e:
        await ctx.respond(e)
        return


@info_plugin.command
@lb.add_checks(
    lb.guild_only,
    lb.has_guild_permissions(hk.Permissions.MANAGE_EVENTS) | lb.owner_only,
)
@lb.option("event", "The event", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command(
    "inevent", "Fetch the list of members interested in an event", pass_options=True
)
@lb.implements(lb.PrefixCommand)
async def inevent_cmd(ctx: lb.Context, event: str):
    try:
        events = event.split()
        if events[-1] == "--export":  # Whether to export the data as a csv
            export = True
            event = " ".join(events[:-1])
        else:
            export = False
            event = " ".join(events)

        probable_event = event

        try:
            probable_event = int(probable_event)
        except ValueError:
            pass

        event_: t.Optional[hk.ScheduledEvent] = None
        events = await ctx.bot.rest.fetch_scheduled_events(ctx.guild_id)
        if isinstance(probable_event, int):
            for event in events:
                if probable_event == event.id:
                    event_ = event
                    break
        else:
            guild_events = {
                event.name: event
                for event in await ctx.bot.rest.fetch_scheduled_events(ctx.guild_id)
            }

            ans = process.extractOne(
                probable_event,
                list(guild_events.keys()),
                score_cutoff=70,
                processor=default_process,
            )

            # Unpacking the closest value, if it exists
            if ans:
                closest_role_match, *_ = ans

                event_ = guild_events[closest_role_match]

        if not event_:
            await ctx.respond("No matching events found")
            return

        event_members = []
        members = list(
            await ctx.bot.rest.fetch_scheduled_event_users(ctx.guild_id, event_)
        )

        if not export:
            for member in members:
                if member.member:
                    event_members.append(
                        f"`{member.member.id: <19}`  {member.member.username}"
                    )

            paginated_members = [
                event_members[i : i + 20] for i in range(0, len(event_members), 20)
            ]
            pages = []

            if not event_members:
                await ctx.respond(
                    hk.Embed(
                        title=f"List of users interested in {event_.name} ({len(event_members)})",
                        timestamp=datetime.now().astimezone(),
                        color=colors.DEFAULT,
                    ).set_image(event_.image_url)
                )

                return

            for item in paginated_members:
                pages.append(
                    hk.Embed(
                        title=f"List of users interested in {event_.name} ({len(event_members)})",
                        timestamp=datetime.now().astimezone(),
                        color=colors.DEFAULT,
                    )
                    .set_image(event_.image_url)
                    .add_field("\u200B", "\n".join(item))
                )

            if len(pages) == 1:
                await ctx.respond(pages[0])
                return

            view = AuthorNavi(pages=pages, user_id=ctx.author.id, buttons="default")
            await view.send(ctx.channel_id)

        else:
            try:
                mem_ids, mem_names = [], []
                for member in members:
                    if member.member:
                        mem_ids.append(member.member.id)
                        mem_names.append(member.member.username)

                test_bytes = io.BytesIO()

                pd.DataFrame({"User IDs": mem_ids, "User Names": mem_names}).to_csv(
                    test_bytes, index=False
                )

                await ctx.respond(hk.Bytes(test_bytes.getvalue(), "event.csv"))

            except Exception as e:
                await ctx.respond(f"Erra: {e}")
    except Exception as e:
        await ctx.respond(f"Error: {e}")


@info_plugin.command
@lb.add_checks(
    lb.guild_only, lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS)
)
@lb.option("query", "The emote to search for", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command(
    "searchemote", "Search for an emote on 7tv", aliases=["se"], pass_options=True
)
@lb.implements(lb.PrefixCommand)
async def search_emote(ctx: lb.Context, query: str) -> None:
    print("Creating session")
    mySevenTvSession = seventv.seventv()
    print("Seventv session created")
    emotes = await mySevenTvSession.emote_search(query, case_sensitive=True)
    print("Emotes fetched")
    try:
        pages = [
            hk.Embed(title=f"Emote: {emote.name}")
            .set_image(f"https:{emote.host_url}/2x.webp")
            .set_footer(text="Powered by 7tv")
            for emote in emotes
        ]

        buttons = [
            CustomPrevButton(),
            nav.IndicatorButton(),
            CustomNextButton(),
            AddEmoteButton(),
            KillNavButton(),
        ]
        navigator = AuthorNavi(pages=pages, user_id=ctx.author.id, buttons=buttons)
    except Exception as e:
        await ctx.respond(e)
        return
    await navigator.send(ctx.channel_id)
    await mySevenTvSession.close()


@info_plugin.command
@lb.add_checks(
    lb.guild_only, lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS)
)
@lb.option("emotes", "The emotes to swipe", modifier=lb.OptionModifier.GREEDY)
@lb.command(
    "swipe",
    "Swipe emotes from one server to another",
    aliases=["copyemote"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand)
async def swipe_emotes(
    ctx: lb.Context, emotes: t.List[t.Union[hk.CustomEmoji, str]]
) -> None:
    try:
        if not emotes:
            await ctx.respond("No emotes found")
            return

        emotes = list(
            {
                hk.Emoji.parse(emote)
                for emote in emotes
                if hk.Emoji.parse(emote) is not None
            }
        )

        for emote in emotes:
            try:
                await ctx.bot.rest.create_emoji(
                    ctx.guild_id, name=emote.name, image=emote
                )
                await ctx.respond(f"Added emote: {emote.mention}")
            except hk.RateLimitTooLongError:
                await ctx.respond("Rate limit hit. Please try again shortly.")
                break
            except hk.BadRequestError:
                # Reason being server emotes full or invalid value
                await ctx.respond("Can't add this emote")
            except hk.InternalServerError:
                await ctx.respond("Discord went buggy oops")
                break

    except Exception as e:
        await ctx.respond(f"Error: {e}")


def check_if_known_emoji_provider(link: str):
    known_providers = [
        ".discordapp.net",
        "cdn.7tv.app",
        "cdn.donmai.us",
        "i.imgur.com",
        "phixiv.net",
        "cdn.discordapp.com",
        "emoji.gg",
    ]

    for provider in known_providers:
        if provider in link:
            return True
    return False


@info_plugin.command
@lb.add_checks(
    lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS), lb.guild_only
)
@lb.option(
    "processor",
    "Pre processors for the image",
    required=False,
    modifier=lb.OptionModifier.GREEDY,
)
@lb.option("emote", "The emote to add")
@lb.option("name", "Name of the emote to add")
@lb.command("addemote", "Add an emote to the server", aliases=["ae"], pass_options=True)
@lb.implements(lb.PrefixCommand)
async def add_emote(
    ctx: lb.Context,
    name: str,
    emote: t.Union[hk.Emoji, str],
    processor: t.Optional[t.List[str]],
) -> None:
    try:
        if len(name) < 2 or len(name) > 32:
            await ctx.respond(
                "Invalid emote name length. Must be between 2 and 32 characters"
            )
            return

        try:
            possible_emote = hk.Emoji.parse(emote)
        except ValueError:
            pass

        if isinstance(possible_emote, hk.CustomEmoji):
            await ctx.respond("Adding...")
            try:
                emoji = await ctx.bot.rest.create_emoji(
                    ctx.guild_id, name=name, image=possible_emote
                )
                await ctx.edit_last_response(f"Added emote: {emoji.mention}")
            except Exception as e:
                await ctx.respond(f"Error: {e}")

            return

        if not check_if_known_emoji_provider(emote):
            return await ctx.respond("Unknown Emote Provider ⚠")

        image_type = await is_image(
            emote, ctx.bot.d.aio_session
        )  # 1 if PIL friendly image, 2 if not, 0 if not image

        if not image_type:
            await ctx.respond("Invalid image url")
            return

        elif image_type == 2:
            try:
                emoji = await ctx.bot.rest.create_emoji(
                    ctx.guild_id, name=name, image=emote
                )
                await ctx.respond(f"Added emote: {emoji.mention}")

            except hk.RateLimitTooLongError:
                await ctx.respond("Rate limit hit. Please try again shortly.")

            except hk.BadRequestError:
                # Reason being server emotes full or invalid value
                await ctx.respond("Can't add this emote")

            except hk.InternalServerError:
                await ctx.respond("Discord went buggy oops")

        elif image_type == 1:
            try:
                async with ctx.bot.d.aio_session.get(emote) as resp:
                    img_bytes = await resp.read()

                    ratio = len(img_bytes) / (1024 * 256)

                    if ratio > 1:
                        await ctx.respond(
                            "Image size possibly too large, attempting compression..."
                        )

                        im = Image.open(io.BytesIO(img_bytes))
                        im = ImageOps.contain(im, (128, 128), Image.Resampling.LANCZOS)

                        new_pixels = io.BytesIO()
                        im.save(new_pixels, format="PNG", optimize=True)
                        emote = new_pixels.getvalue()

                    else:
                        pass

                emoji = await ctx.bot.rest.create_emoji(
                    ctx.guild_id, name=name, image=emote
                )
                await ctx.respond(f"Added emote: {emoji.mention}")

            except hk.RateLimitTooLongError:
                await ctx.respond("Rate limit hit. Please try again shortly.")

            except hk.BadRequestError:
                # Reason being server emotes full or invalid value
                await ctx.respond("Can't add this emote")

            except hk.InternalServerError:
                await ctx.respond("Discord went buggy oops")

    except Exception as e:
        await ctx.respond(f"Error: {e}")


@info_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("guilds", "See the servers the bot's in")
@lb.implements(lb.PrefixCommand)
async def guilds(ctx: lb.Context) -> None:
    """Fetch a list of guilds the bot is in

    Args:
        ctx (lb.Context): The context for the command
    """

    pages = []

    for gld in list([guild for guild in ctx.bot.cache.get_guilds_view().values()]):
        pages.append(
            hk.Embed(
                color=colors.DAWN_PINK,
                title=f"Server: {gld.name}",
                description=f"Server ID: `{gld.id}`",
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Owner", await gld.fetch_owner(), inline=True)
            .add_field(
                "Server Created",
                f"<t:{int(gld.created_at.timestamp())}:R>",
                inline=True,
            )
            .add_field("Member Count", gld.member_count)
            .add_field("Boosts", gld.premium_subscription_count or "NA", inline=True)
            .add_field("Boost Level", gld.premium_tier or "NA", inline=True)
            .set_thumbnail(gld.icon_url)
            .set_image(gld.banner_url)
        )

    navigator = AuthorNavi(pages=pages, user_id=ctx.author.id)
    await navigator.send(ctx.channel_id)


@info_plugin.command
@lb.add_checks(lb.owner_only, lb.guild_only)
@lb.option("user", "The user duh", t.Optional[hk.Member], required=False)
@lb.command("userinfo", "Find information about a user", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def user_info(ctx: lb.Context, user: hk.Member) -> None:
    user = user or ctx.member

    try:
        presence = user.get_presence()

        if presence.activities and len(presence.activities) != 0:
            activity = f"{presence.activity.type} {presence.activity.name}"
        else:
            activity = presence.visible_status

        roles = (await user.fetch_roles())[1:]

        await ctx.respond(
            hk.Embed(
                title=f"User: {user.display_name}",
                description=f"User ID: `{user.id}`",
                colour=colors.DEFAULT,
                timestamp=datetime.now().astimezone(),
            )
            .set_footer(
                text=f"Requested by {ctx.author.username}",
                icon=ctx.author.display_avatar_url,
            )
            .add_field(
                "Bot?",
                "Yes" if user.is_bot else "No",
                inline=True,
            )
            .add_field(
                "Account Created",
                f"<t:{int(user.created_at.timestamp())}:R>",
                inline=True,
            )
            .add_field(
                "Server Joined",
                f"<t:{int(user.joined_at.timestamp())}:R>",
                inline=True,
            )
            .add_field(
                "Roles",
                ", ".join(r.mention for r in roles),
                inline=False,
            )
            .set_thumbnail(user.avatar_url)
            .set_image(user.banner_url)
        )

        await ctx.respond(activity)

    except Exception as e:
        await ctx.respond(e)


@info_plugin.command
@lb.add_cooldown(10, 1, lb.UserBucket)
@lb.add_cooldown(15, 2, lb.ChannelBucket)
@lb.command("botinfo", "Get general info about the bot", aliases=["info"])
@lb.implements(lb.PrefixCommand)
async def botinfo(ctx: lb.Context) -> None:
    """Get info about the bot"""

    try:
        user = ctx.bot.get_me()
        data = await ctx.bot.rest.fetch_application()
        guilds = list(ctx.bot.cache.get_guilds_view().values())

        member = 0
        for guild in list(ctx.bot.cache.get_members_view()):
            guild_obj = ctx.bot.cache.get_guild(guild)
            member = member + guild_obj.member_count

        process = Popen(
            "git rev-list --count main",
            text=True,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
        )
        num_commits, _ = process.communicate()

        num_commits = int(num_commits)

        process = Popen(
            'git log -5 --format="<t:%at:D>: %s"',
            text=True,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
        )
        changes, _ = process.communicate()

        change_list: t.List[str] = [
            f"{i+1}. {item}" for i, item in enumerate(changes.split("\n")[:5])
        ]

        changes = "\n".join(change_list)

        version = f"0.{floor(num_commits/100)}.{floor((num_commits%100)/10)}"

        pages = [
            hk.Embed(
                color=colors.DEFAULT,
                description="A multi-purpose discord bot \
                    written in hikari-py.\n\nPrimarily made for the Oshi no Ko discord server.",
            )
            .add_field("Name", user)
            .add_field("No of Servers", len(guilds), inline=True)
            .add_field("No of Members", member, inline=True)
            .add_field("Version", version)
            .add_field(
                "Alive since", f"<t:{int(user.created_at.timestamp())}:R>", inline=True
            )
            .add_field(
                "Up since",
                f"<t:{int(ctx.bot.d.timeup.timestamp())}:R>",
                inline=True,
            )
            .add_field(
                "System Usage",
                f"RAM: {psutil.virtual_memory()[2]}% (of 512MB) \nCPU: {psutil.cpu_percent(4)}%",
            )
            .set_author(name=f"{user.username} Bot")
            .set_thumbnail(user.avatar_url)
            .set_footer(f"Made by: {data.owner}", icon=data.owner.avatar_url),
            hk.Embed(description=changes, color=colors.DEFAULT).set_author(
                name="Bot Changelog (Recent)"
            ),
        ]

        view = AuthorView(user_id=ctx.author.id)
        view.add_item(
            SwapButton(
                label1="Changelogs",
                label2="Info",
                emoji1=hk.Emoji.parse("<:MIU_changelog:1108056158377349173>"),
                emoji2=hk.Emoji.parse("ℹ️"),
                original_page=pages[0],
                swap_page=pages[1],
            )
        )

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


@info_plugin.command
@lb.add_checks(
    lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS), lb.guild_only
)
@lb.command("stickerinfo", "Get info about a sticker", aliases=["sticker"])
@lb.implements(lb.PrefixCommand)
async def sticker_info(ctx: lb.Context) -> None:
    """Fetch info about a sticker (guild or otherwise)

    Args:
        ctx (lb.Context): The context (should have a sticker in the message)
    """
    resp_embed = []
    if not ctx.event.message.stickers:
        await ctx.respond("No sticker in your message, I'm afraid")
        return

    stickers = []

    for sticker in ctx.event.message.stickers:
        try:
            sticker = await ctx.bot.rest.fetch_sticker(sticker.id)
            stickers.append(sticker)
        except hk.NotFoundError:
            resp_embed.append(
                hk.Embed(
                    color=colors.WARN,
                    title=f"Sticker: {sticker.name}",
                    timestamp=datetime.now().astimezone(),
                )
                .add_field("Sticker ID: ", f"`{sticker.id}`")
                .add_field("Created at", f"<t:{int(sticker.created_at.timestamp())}:R>")
                .set_image(sticker.image_url)
            )
        else:
            resp_embed.append(
                hk.Embed(
                    color=colors.DEFAULT,
                    title=f"Sticker: {sticker.name}",
                    timestamp=datetime.now().astimezone(),
                )
                .add_field("Sticker ID: ", f"`{sticker.id}`")
                .add_field(
                    "Created at",
                    f"<t:{int(sticker.created_at.timestamp())}:R>",
                    inline=True,
                )
                .add_field("Type", sticker.type, inline=True)
                .add_field("Tag", f":{sticker.tag}:")
                .set_thumbnail(ctx.get_guild().icon_url)
                .set_image(sticker.image_url)
            )

    await ctx.respond(embeds=resp_embed)


@info_plugin.command
@lb.command(
    "emoteinfo", "Get info about an emote", aliases=["emote"], pass_options=True
)
@lb.implements(lb.PrefixCommand)
async def emote_info(
    ctx: lb.Context,
) -> None:
    """Fetch basic info about upto 5 emotes

    Args:
        ctx (lb.Context): The context in which the command is invoked
    """
    emotes = []
    for word in ctx.event.message.content.split(" "):
        try:
            emote = hk.Emoji.parse(word)
            if isinstance(emote, hk.CustomEmoji):
                emotes.append(emote)

        except ValueError:
            continue

    emotes = list(set(emotes))

    if not emotes:
        await ctx.respond("No emotes found")
        return
    elif len(emotes) > 5:
        await ctx.respond("Too many emotes, taking the first 5 into account")

    resp_embed = []
    for emote in emotes[:5]:
        resp_embed.append(
            hk.Embed(title=f"Emoji: {emote.name}")
            .add_field("Raw", f"`{emote.mention}`")
            .set_thumbnail(emote.url)
        )

    await ctx.respond(
        embeds=resp_embed,
    )


@info_plugin.command
@lb.add_checks(lb.has_guild_permissions(hk.Permissions.ADMINISTRATOR), lb.guild_only)
@lb.command("removesticker", "Remove a sticker", aliases=["rst"])
@lb.implements(lb.PrefixCommand)
async def sticker_removal(ctx: lb.MessageContext):
    if not ctx.event.message.stickers:
        await ctx.respond("No sticker in your message, I'm afraid")
        return

    sticker_partial = ctx.event.message.stickers[0]

    if isinstance(sticker_partial, hk.GuildSticker):
        await ctx.respond("Dance")

    try:
        sticker = await ctx.bot.rest.fetch_sticker(sticker_partial.id)

        sticker_image = await ctx.bot.d.aio_session.get(sticker.image_url)

        ext = sticker.image_url.split(".")[-1]
        await ctx.author.send(
            hk.Embed(
                title="STICKER REMOVAL NOTIFICATION",
                color=colors.ERROR,
                description=f"Sticker `{sticker.name}` removed from `{ctx.get_guild()}`",
                timestamp=datetime.now().astimezone(),
            ).set_image(
                hk.Bytes(
                    io.BytesIO(await sticker_image.read()),
                    f"{sticker.name}_archive.{ext}",
                )
            )
        )

        await ctx.bot.rest.delete_sticker(ctx.guild_id, sticker_partial)
        await ctx.respond(f"Removed sticker: `{sticker.name}`")

    except hk.NotFoundError:
        await ctx.respond("Sticker not present in the server")

    except hk.InternalServerError:
        await ctx.respond("A hiccup from discord's side, please try again")


@info_plugin.command
@lb.add_checks(
    lb.bot_has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS),
    lb.has_guild_permissions(hk.Permissions.ADMINISTRATOR),
)
@lb.command(
    "removeemote",
    "Remove emote or multiple, simple as that",
    aliases=["re", "remote"],
    pass_options=True,
    # hidden=True,
)
@lb.implements(lb.PrefixCommand)
async def emote_removal(
    ctx: lb.Context,
) -> None:
    """Remove multiple emotes from a guild

    Args:
        ctx (:obj:`lb.Context`): The context in which the command is invoked
        (should have the emotes in the message)
    """

    try:
        words = ctx.event.message.content.split(" ")
        if len(words) == 1:
            await ctx.respond(
                hk.Embed(
                    title="Remove emote help",
                    description=(
                        "Remove an emote or multiple, simple as that (upto 5)"
                        "\n\n"
                        "Usage: `-re <emote1> <emote2>....`"
                    ),
                )
            )
            return
        emotes = []
        for word in words[1:]:
            try:
                emote = hk.Emoji.parse(word)
                emote = await ctx.bot.rest.fetch_emoji(ctx.guild_id, emoji=emote)

                emotes.append(emote)

            except ValueError:
                continue

            except hk.NotFoundError:
                continue

        emotes = list(set(emotes))

        if not emotes:
            await ctx.respond("No emotes found")
            return

        if len(emotes) > 5:
            await ctx.respond("Too many emotes, removing the first five at once")
    except Exception as e:
        await ctx.respond(f"Early {e}")

    for emote in emotes[:5]:
        try:
            ext = emote.url.split(".")[-1]
            await ctx.author.send(
                hk.Embed(
                    title="EMOTE REMOVAL NOTIFICATION",
                    color=colors.ERROR,
                    description=f"Emote `{emote.name}` removed from `{ctx.get_guild()}`",
                    timestamp=datetime.now().astimezone(),
                ).set_image(
                    hk.Bytes(
                        io.BytesIO(await emote.read()), f"{emote.name}_archive.{ext}"
                    )
                )
            )
            await ctx.bot.rest.delete_emoji(ctx.guild_id, emote)
            await ctx.respond(f"Removed emote: `{emote.name}`")
        except Exception as e:
            await ctx.respond(f"Error: {e}")


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(info_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(info_plugin)
