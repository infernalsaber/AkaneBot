"""Emote management commands for AkaneBot."""
import io
import time
import typing as t
from datetime import datetime

import hikari as hk
import lightbulb as lb
from miru.ext import nav
from PIL import Image, ImageOps
from rapidfuzz import process
from rapidfuzz.utils import default_process

from utils.buttons import (
    AddEmoteButton,
    CustomNextButton,
    CustomPrevButton,
    KillNavButton,
)
from utils.emotes_helper import (
    add_emoji_from_source,
    check_if_known_emoji_provider,
    format_emote_error,
    sanitize_emoji_name,
)
from utils.errors import SevenTVError
from utils.misc import check_if_url, is_image
from utils.models import ColorPalette as colors
from utils.seventv import SevenTVClient, SevenTVEmote
from utils.views import AuthorNavi

emotes_plugin = lb.Plugin("Emotes", "Emote management commands", include_datastore=True)
emotes_plugin.d.help = True
emotes_plugin.d.help_emoji = "😀"
emotes_plugin.d.help_image = "https://i.imgur.com/nsg3lZJ.png"


@emotes_plugin.command
@lb.add_checks(
    lb.guild_only, lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS)
)
@lb.option("query", "The emote to search for", modifier=lb.OptionModifier.CONSUME_REST)
@lb.command(
    "searchemote", "Search for an emote on 7tv", aliases=["se"], pass_options=True
)
@lb.implements(lb.PrefixCommand)
async def search_emote(ctx: lb.Context, query: str) -> None:
    """Search for emotes on 7TV and add them using interactive navigation."""
    session = getattr(ctx.bot.d, "aio_session", None)
    client = SevenTVClient(session=session)
    try:
        emotes = await client.search_emotes(query)
    except SevenTVError as e:
        await ctx.respond(f"❌ Failed to search 7TV: {e}")
        return
    except Exception as e:
        await ctx.respond(f"❌ Error searching 7TV: {e}")
        return

    if not emotes:
        await ctx.respond(f"No emotes found for `{query}` on 7TV.")
        return

    pages = [emote.to_embed() for emote in emotes]
    buttons = [
        CustomPrevButton(),
        nav.IndicatorButton(),
        CustomNextButton(),
        AddEmoteButton(),
        KillNavButton(),
    ]
    navigator = AuthorNavi(pages=pages, user_id=ctx.author.id, buttons=buttons)
    await navigator.send(ctx.channel_id)



@emotes_plugin.command
@lb.add_checks(
    lb.guild_only, lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS)
)
@lb.option("emotes", "The emotes to swipe", modifier=lb.OptionModifier.GREEDY)
@lb.command(
    "swipe",
    "Swipe emotes from one server to another",
    aliases=["copyemote", "ce"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand)
async def swipe_emotes(
    ctx: lb.Context, emotes: t.List[t.Union[hk.CustomEmoji, str]]
) -> None:
    if not ctx.guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    if not emotes:
        await ctx.respond("No emotes found")
        return

    parsed_emotes: list[hk.CustomEmoji] = []
    for raw in emotes:
        if isinstance(raw, hk.CustomEmoji):
            if raw not in parsed_emotes:
                parsed_emotes.append(raw)
        elif isinstance(raw, str):
            try:
                parsed = hk.Emoji.parse(raw)
                if isinstance(parsed, hk.CustomEmoji) and parsed not in parsed_emotes:
                    parsed_emotes.append(parsed)
            except ValueError:
                continue

    if not parsed_emotes:
        await ctx.respond("No valid custom emotes found to swipe.")
        return

    added_emotes: list[hk.KnownCustomEmoji] = []
    failed_emotes: list[str] = []
    rate_limit_msg: t.Optional[str] = None

    for idx, emote in enumerate(parsed_emotes):
        try:
            new_emoji = await add_emoji_from_source(ctx, emote)
            added_emotes.append(new_emoji)
        except hk.RateLimitTooLongError as e:
            rate_limit_msg = format_emote_error(e)
            remaining_count = len(parsed_emotes) - idx
            if remaining_count > 1:
                failed_emotes.append(f"`{emote.name}` (+ {remaining_count - 1} remaining skipped due to rate limit)")
            else:
                failed_emotes.append(f"`{emote.name}` (rate limit reached)")
            break
        except hk.BadRequestError:
            failed_emotes.append(f"`{emote.name}` (server slots full or invalid format)")
        except hk.ForbiddenError:
            failed_emotes.append(f"`{emote.name}` (missing permissions)")
        except Exception as e:
            failed_emotes.append(f"`{emote.name}` ({e})")

    response_lines: list[str] = []
    if added_emotes:
        mentions = " ".join(e.mention for e in added_emotes)
        response_lines.append(f"Added {len(added_emotes)} emote{'s' if len(added_emotes) != 1 else ''}: {mentions}")

    if failed_emotes:
        fail_list = "\n".join(f"- {item}" for item in failed_emotes)
        response_lines.append(f"Failed ({len(failed_emotes)}):\n{fail_list}")

    if rate_limit_msg:
        response_lines.append(rate_limit_msg)

    if not response_lines:
        await ctx.respond("No emotes were added.")
        return

    await ctx.respond("\n\n".join(response_lines))


@emotes_plugin.command
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
    processor: t.Optional[t.List[str]] = None,
) -> None:
    if not ctx.guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    try:
        new_emoji = await add_emoji_from_source(ctx, emote, name=name)
        await ctx.respond(f"Added emote: {new_emoji.mention}")
    except Exception as e:
        await ctx.respond(format_emote_error(e))


@emotes_plugin.command
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


@emotes_plugin.command
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


# @emotes_plugin.command
# @lb.command("emote", "Emote management commands")
# @lb.implements(lb.SlashCommandGroup)
# async def emote_group(ctx: lb.Context) -> None:
#     """Group command for emote management."""
#     pass
# 
# 
# @emote_group.child
# @lb.add_checks(
#     lb.guild_only,
#     lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS),
# )
# @lb.option("name", "The emote to remove", autocomplete=True)
# @lb.command("remove", "Remove an emote from the server", pass_options=True)
# @lb.implements(lb.SlashSubCommand)
# async def emote_remove_slash(ctx: lb.SlashContext, name: str) -> None:
#     """Remove an emote from the current guild"""
#     if not ctx.guild_id:
#         await ctx.respond("This command can only be used in a server.")
#         return
# 
#     try:
#         guild_emojis = await ctx.bot.rest.fetch_guild_emojis(ctx.guild_id)
#         target_emoji = None
#         for emoji in guild_emojis:
#             if emoji.name == name or str(emoji.id) == name:
#                 target_emoji = emoji
#                 break
# 
#         if not target_emoji:
#             await ctx.respond(f"Emote `{name}` not found in this server.")
#             return
# 
#         try:
#             ext = target_emoji.url.split(".")[-1]
#             guild_obj = ctx.get_guild()
#             guild_name = guild_obj.name if guild_obj else "Server"
#             await ctx.author.send(
#                 hk.Embed(
#                     title="EMOTE REMOVAL NOTIFICATION",
#                     color=colors.ERROR,
#                     description=f"Emote `{target_emoji.name}` removed from `{guild_name}`",
#                     timestamp=datetime.now().astimezone(),
#                 ).set_image(
#                     hk.Bytes(
#                         io.BytesIO(await target_emoji.read()), f"{target_emoji.name}_archive.{ext}"
#                     )
#                 )
#             )
#         except Exception:
#             pass
# 
#         await ctx.bot.rest.delete_emoji(ctx.guild_id, target_emoji.id)
#         await ctx.respond(f"Removed emote: `{target_emoji.name}`")
#     except Exception as e:
#         await ctx.respond(f"Error removing emote: {e}")
# 
# 
# @emote_remove_slash.autocomplete("name")
# async def emote_remove_autocomplete(
#     option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
# ) -> t.Sequence[str]:
#     if not interaction.guild_id:
#         return []
# 
#     try:
#         guild_emojis = await interaction.app.rest.fetch_guild_emojis(interaction.guild_id)
#         emoji_names = [emoji.name for emoji in guild_emojis if emoji.name]
# 
#         if not option.value or not str(option.value).strip():
#             return emoji_names[:25]
# 
#         matches = process.extract(
#             str(option.value),
#             emoji_names,
#             score_cutoff=40,
#             limit=25,
#             processor=default_process,
#         )
#         return [match[0] for match in matches]
#     except Exception:
#         return []
# 
# 
# @emote_group.child
# @lb.add_checks(
#     lb.guild_only,
#     lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS),
# )
# @lb.option("image", "Image file to upload for the emote", type=hk.Attachment, required=False)
# @lb.option("url", "URL or custom emote link to add", required=False)
# @lb.option("name", "Name of the emote to add")
# @lb.command("add", "Add an emote to the server", pass_options=True)
# @lb.implements(lb.SlashSubCommand)
# async def emote_add_slash(
#     ctx: lb.SlashContext,
#     name: str,
#     url: t.Optional[str] = None,
#     image: t.Optional[hk.Attachment] = None,
# ) -> None:
#     """Add an emote to the server via URL or image attachment"""
#     if not ctx.guild_id:
#         await ctx.respond("This command can only be used in a server.")
#         return
# 
#     if not url and not image:
#         await ctx.respond("Please provide either a `url` or an `image` attachment.")
#         return
# 
#     source = image if image is not None else url
#     try:
#         new_emoji = await add_emoji_from_source(ctx, source, name=name)
#         await ctx.respond(f"Added emote: {new_emoji.mention}")
#     except Exception as e:
#         await ctx.respond(format_emote_error(e))
# 
# 
# @emote_group.child
# @lb.add_checks(
#     lb.guild_only,
#     lb.has_guild_permissions(hk.Permissions.MANAGE_GUILD_EXPRESSIONS),
# )
# @lb.option("query", "The emote name to search for")
# @lb.command("search", "Search for an emote on 7tv", pass_options=True)
# @lb.implements(lb.SlashSubCommand)
# async def emote_search_slash(ctx: lb.SlashContext, query: str) -> None:
#     """Search for an emote on 7tv and add it to the server"""
#     session = getattr(ctx.bot.d, "aio_session", None)
#     client = SevenTVClient(session=session)
#     try:
#         emotes = await client.search_emotes(query)
#     except SevenTVError as e:
#         await ctx.respond(f"❌ Failed to search 7TV: {e}")
#         return
#     except Exception as e:
#         await ctx.respond(f"❌ Error searching 7TV: {e}")
#         return
# 
#     if not emotes:
#         await ctx.respond(f"No emotes found for `{query}` on 7TV.")
#         return
# 
#     pages = [emote.to_embed() for emote in emotes]
#     buttons = [
#         CustomPrevButton(),
#         nav.IndicatorButton(),
#         CustomNextButton(),
#         AddEmoteButton(),
#         KillNavButton(),
#     ]
#     navigator = AuthorNavi(pages=pages, user_id=ctx.author.id, buttons=buttons)
#     await navigator.send(ctx.interaction)
# 
# 
# 
# @emote_group.child
# @lb.option("emote", "The emote (or emote mention/name) to get info for", autocomplete=True)
# @lb.command("info", "Get info about an emote", pass_options=True)
# @lb.implements(lb.SlashSubCommand)
# async def emote_info_slash(ctx: lb.SlashContext, emote: str) -> None:
#     """Fetch basic info about an emote"""
#     parsed_emotes = []
# 
#     try:
#         parsed = hk.Emoji.parse(emote)
#         if isinstance(parsed, hk.CustomEmoji):
#             parsed_emotes.append(parsed)
#     except ValueError:
#         pass
# 
#     if not parsed_emotes and ctx.guild_id:
#         try:
#             guild_emojis = await ctx.bot.rest.fetch_guild_emojis(ctx.guild_id)
#             for e in guild_emojis:
#                 if e.name == emote or str(e.id) == emote:
#                     parsed_emotes.append(e)
#                     break
#         except Exception:
#             pass
# 
#     if not parsed_emotes:
#         await ctx.respond(f"No custom emote found for `{emote}`.")
#         return
# 
#     resp_embeds = []
#     for e in parsed_emotes[:5]:
#         embed = (
#             hk.Embed(title=f"Emoji: {e.name}")
#             .add_field("ID", f"`{e.id}`", inline=True)
#             .add_field("Raw", f"`{e.mention}`", inline=True)
#             .set_thumbnail(e.url)
#         )
#         resp_embeds.append(embed)
# 
#     await ctx.respond(embeds=resp_embeds)
# 
# 
# @emote_info_slash.autocomplete("emote")
# async def emote_info_autocomplete(
#     option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
# ) -> t.Sequence[str]:
#     if not interaction.guild_id:
#         return []
# 
#     try:
#         guild_emojis = await interaction.app.rest.fetch_guild_emojis(interaction.guild_id)
#         emoji_names = [emoji.name for emoji in guild_emojis if emoji.name]
# 
#         if not option.value or not str(option.value).strip():
#             return emoji_names[:25]
# 
#         matches = process.extract(
#             str(option.value),
#             emoji_names,
#             score_cutoff=40,
#             limit=25,
#             processor=default_process,
#         )
#         return [match[0] for match in matches]
#     except Exception:
#         return []


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(emotes_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(emotes_plugin)
