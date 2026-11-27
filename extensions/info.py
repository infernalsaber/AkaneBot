"""Get information about a role, server, user, bot etc."""
import asyncio
import io
import json
import re
import typing as t
from datetime import datetime
from pathlib import Path
from subprocess import PIPE, Popen

import aiohttp
import hikari as hk
import lightbulb as lb
import miru
import pandas as pd
import psutil
from miru.ext import nav
from PIL import Image, ImageOps
from rapidfuzz import process
from rapidfuzz.utils import default_process

from utils.buttons import (
    AddEmoteButton,
    CustomNextButton,
    CustomPrevButton,
    KillNavButton,
    SwapButton,
)
from utils.models import ColorPalette as colors
from utils.models import EmoteCollection as emotes
from utils.templates import CUSTOM_EMOJI, render
from utils.views import AuthorNavi, AuthorView

info_plugin = lb.Plugin("Utility", "Utility and info commands", include_datastore=True)
info_plugin.d.help = True
info_plugin.d.help_emoji = "⚙️"
info_plugin.d.help_image = "https://i.imgur.com/nsg3lZJ.png"

PRIVACY_POLICY_URL = "https://gist.github.com/infernalsaber/25f7067b02b291f432f9195094daab35"



@info_plugin.command
@lb.add_checks(lb.guild_only)
@lb.option("role", "The role", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command("inrole", "List of users in role", pass_options=True)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
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

        if isinstance(ctx, lb.SlashContext):
            await view.send(ctx.interaction)
        else:
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


def _git(cmd: str) -> t.Optional[str]:
    """Run a git command, returning its stripped output or None if git/the repo is unavailable"""
    try:
        process = Popen(cmd, text=True, shell=True, stdout=PIPE, stderr=PIPE)
        out, _ = process.communicate()
    except OSError:
        return None
    return out.strip() if process.returncode == 0 and out.strip() else None


@info_plugin.command
@lb.add_cooldown(10, 1, lb.UserBucket)
@lb.add_cooldown(15, 2, lb.ChannelBucket)
@lb.command(
    "botinfo", "Get general info about the bot", aliases=["info"], auto_defer=True
)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def botinfo(ctx: lb.Context) -> None:
    """Get info about the bot"""

    try:
        bot_process = psutil.Process()
        # First call only starts the measurement window, it always returns 0.0
        bot_process.cpu_percent()

        user = ctx.bot.get_me()
        data = await ctx.bot.rest.fetch_application()
        guilds = list(ctx.bot.cache.get_guilds_view().values())

        member = 0
        for guild in list(ctx.bot.cache.get_members_view()):
            guild_obj = ctx.bot.cache.get_guild(guild)
            member = member + guild_obj.member_count

        build_info = Path("build_info.json")
        if build_info.exists():
            info = json.loads(build_info.read_text())
            version = info["version"]
            changes = "\n".join(
                f"<t:{change['timestamp']}:D>: {change['message']}"
                for change in info["changes"]
            )
        else:
            version = _git("git describe --tags --abbrev=0") or "unknown"
            changes = _git('git log -5 --format="<t:%at:D>: %s"')

        if changes:
            changes = "\n".join(
                f"{i+1}. {item}" for i, item in enumerate(changes.split("\n")[:5])
            )
        else:
            changes = "Change log unavailable (no local git)."

        pages = [
            hk.Embed(
                color=colors.DEFAULT,
                description="A multi-purpose discord bot \
                    written in hikari-py.",
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
                f"RAM: {bot_process.memory_info().rss / 1024**2:.0f} MB\n"
                f"CPU: measuring… {hk.Emoji.parse(emotes.LOADING.value)}",
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
        view.add_item(
            miru.Button(
                style=hk.ButtonStyle.LINK,
                url=PRIVACY_POLICY_URL,
                label="Privacy Policy",
                emoji="🔒",
            )
        )

        choice = await ctx.respond(
            embed=pages[0],
            components=view,
        )
        await view.start(choice)

        await asyncio.sleep(3)
        # Edit the same embed object so the swap button keeps the updated usage
        pages[0].fields[-1].value = (
            f"RAM: {bot_process.memory_info().rss / 1024**2:.0f} MB\n"
            f"CPU: {bot_process.cpu_percent()}%"
        )
        await ctx.edit_last_response(embed=pages[0])
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


ECHO_MODES = {"Keven": "keven", "Grok": "grok", "Ushiromiya Battler": "umineko"}
MENTION = re.compile(r"<(@!?|#|@&)(\d+)>")


async def plain_mentions(ctx: lb.Context, text: str) -> str:
    """Mentions as Discord shows them (@display name, #channel, @role), since they'd show up raw in an image"""
    names = {}
    for kind, snowflake in set(MENTION.findall(text)):
        entity_id = int(snowflake)
        prefix = "#" if kind == "#" else "@"
        try:
            if kind == "#":
                entity = ctx.bot.cache.get_guild_channel(entity_id) or await ctx.bot.rest.fetch_channel(entity_id)
                name = entity.name
            elif kind == "@&":
                name = ctx.bot.cache.get_role(entity_id).name
            else:
                name = (await member_or_user(ctx, entity_id)).display_name
        except (AttributeError, hk.HTTPError):
            name = "unknown"
        # @everyone's role name already carries the @
        names[kind, snowflake] = f"{prefix}{(name or 'unknown').lstrip('@')}"
    return MENTION.sub(lambda match: names[match.groups()], text)


async def member_or_user(ctx: lb.Context, user_id: int) -> hk.User:
    """The guild member (for their nickname) if they're in this server, else the user"""
    if ctx.guild_id:
        member = ctx.bot.cache.get_member(ctx.guild_id, user_id)
        if member:
            return member
        try:
            return await ctx.bot.rest.fetch_member(ctx.guild_id, user_id)
        except hk.NotFoundError:
            pass
    return ctx.bot.cache.get_user(user_id) or await ctx.bot.rest.fetch_user(user_id)


async def fetch_custom_emoji(ctx: lb.Context, text: str) -> dict[str, bytes]:
    """Images of the custom emoji in `text` keyed by id; animated ones come as their first frame"""

    async def fetch(emoji_id: str) -> tuple[str, bytes | None]:
        try:
            resp = await ctx.bot.d.aio_session.get(f"https://cdn.discordapp.com/emojis/{emoji_id}.webp")
            return emoji_id, await resp.read() if resp.ok else None
        except aiohttp.ClientError:
            return emoji_id, None

    ids = {match[2] for match in CUSTOM_EMOJI.finditer(text)}
    results = await asyncio.gather(*(fetch(emoji_id) for emoji_id in ids))
    return {emoji_id: data for emoji_id, data in results if data}


async def render_mode(ctx: lb.Context, mode: str, text: str) -> hk.Bytes:
    """`text` rendered into the template for `mode` (an ECHO_MODES label), mentions and custom emoji resolved"""
    text = await plain_mentions(ctx, text)
    custom_emoji = await fetch_custom_emoji(ctx, text)
    image = await asyncio.to_thread(render, ECHO_MODES[mode], text, custom_emoji)
    return hk.Bytes(image, f"{ECHO_MODES[mode]}.png")


@info_plugin.command
@lb.option("mode", "Say it as someone else", required=False, choices=list(ECHO_MODES))
@lb.option("message", "What to say")
@lb.command("echo", "Echo a message back", pass_options=True)
@lb.implements(lb.SlashCommand)
async def echo_cmd(ctx: lb.SlashContext, message: str, mode: str | None) -> None:
    """Echo the invoking user's message, optionally rendered into a template"""

    if mode:
        await ctx.respond(hk.ResponseType.DEFERRED_MESSAGE_CREATE)
        await ctx.respond(attachment=await render_mode(ctx, mode, message))
        return

    await ctx.respond(
        f"{ctx.author.mention} said: {message}",
        user_mentions=False,
        role_mentions=False,
        mentions_everyone=False,
    )


class QuoteSelect(miru.TextSelect):
    """Dropdown to pick who Quote renders the message as"""

    async def callback(self, ctx: miru.ViewContext) -> None:
        self.view.answer = self.values[0]
        await ctx.edit_response(content=f"Quoting as **{self.view.answer}**...", components=[])
        self.view.stop()


@info_plugin.command
@lb.command("Quote", "Quote a message as Keven, Grok or Battler", auto_defer=False)
@lb.implements(lb.MessageCommand)
async def quote_menu(ctx: lb.MessageContext) -> None:
    """Render the target message into a template picked from a dropdown; the dropdown message becomes the image"""

    message_link = ctx.options["target"].make_link(ctx.guild_id)
    text = ctx.options["target"].content or "(There's nothing in here)"
    view = AuthorView(user_id=ctx.author.id, timeout=60, clean_items=False)
    view.add_item(QuoteSelect(options=[miru.SelectOption(label=mode) for mode in ECHO_MODES], placeholder="Quote as..."))
    response = await ctx.respond("Select Mode:", components=view)
    await view.start(response)
    await view.wait()

    if view.answer is None:
        await ctx.interaction.edit_initial_response("Timed out", components=[])
        return

    image = await render_mode(ctx, view.answer, text)
    link_view = miru.View()
    link_view.add_item(miru.Button(style=hk.ButtonStyle.LINK, url=message_link, label="Original Message"))
    await ctx.interaction.edit_initial_response(content=None, attachment=image, components=link_view)


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(info_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(info_plugin)
