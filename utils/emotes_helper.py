"""Helper functions for emote processing and guild emoji management."""
from __future__ import annotations

import io
import re
import time
import typing as t

import hikari as hk
from PIL import Image, ImageOps

from utils.misc import check_if_url, is_image


def sanitize_emoji_name(name: str) -> str:
    """Sanitize a name to be valid for Discord emoji (2-32 alphanumeric or underscore characters)."""
    if not name:
        return "emote"

    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")

    if len(sanitized) < 2:
        if sanitized:
            sanitized = f"emote_{sanitized}"
        else:
            sanitized = "emote"

    if len(sanitized) > 32:
        sanitized = sanitized[:32].rstrip("_")
        if len(sanitized) < 2:
            sanitized = "emote"

    return sanitized


def check_if_known_emoji_provider(link: str) -> bool:
    """Check if the provided image URL belongs to a known and trusted emoji provider."""
    known_providers = [
        ".discordapp.net",
        "cdn.7tv.app",
        "cdn.donmai.us",
        "i.imgur.com",
        "phixiv.net",
        "cdn.discordapp.com",
        "emoji.gg",
        "7tv.app",
        "7tv.io",
    ]

    for provider in known_providers:
        if provider in link:
            return True
    return False


def format_emote_error(error: Exception) -> str:
    """Format emote management exceptions into user-friendly messages with TTL when applicable."""
    if isinstance(error, hk.RateLimitTooLongError):
        
        msg = "Rate limit reached for emoji creations❗"
        
        ttl = error.retry_after
        if ttl and ttl > 0:
            reset_ts = int(time.time() + ttl)
            msg += f" You can add more emotes <t:{reset_ts}:R>"
        return msg
    elif isinstance(error, hk.BadRequestError):
        return "❌ Failed to add emote (server emote slots are full or invalid file format/name)."
    elif isinstance(error, hk.ForbiddenError):
        return "❌ Missing permissions to manage emojis/expressions in this server."
    elif isinstance(error, hk.InternalServerError):
        return "❌ Discord server error occurred while adding emote. Please try again later."
    elif isinstance(error, ValueError):
        return f"{error} ⚠️"
    return f"❌ Error: {error}"


async def get_remaining_slots(ctx: t.Any) -> list[int]:
    """Fetch remaining [static_free, animated_free] emote slots directly from REST."""
    guild = await ctx.bot.rest.fetch_guild(ctx.guild_id)
    limit = {0: 50, 1: 100, 2: 150, 3: 250}.get(int(guild.premium_tier), 50)
    emojis = guild.emojis.values()
    return [limit - sum(not e.is_animated for e in emojis), limit - sum(e.is_animated for e in emojis)]


async def add_emoji_from_source(
    ctx: t.Any,
    source: t.Union[hk.CustomEmoji, hk.Attachment, str, bytes],
    name: t.Optional[str] = None,
) -> hk.KnownCustomEmoji:
    """Unified backend helper to resolve image source, process/compress if needed,
    and create the emoji on the guild.

    Returns the newly created KnownCustomEmoji.
    """
    guild_id = getattr(ctx, "guild_id", None)
    if not guild_id:
        raise ValueError("This command can only be used in a server.")

    # 0. If source is string, check if mention / custom emoji string: <:name:id> or <a:name:id>
    if isinstance(source, str):
        try:
            parsed = hk.Emoji.parse(source)
            if isinstance(parsed, hk.CustomEmoji):
                source = parsed
        except ValueError:
            pass

    # 1. If the source is an emote itself, add it (fallback to url if direct add fails)
    if isinstance(source, hk.CustomEmoji):
        raw_name = name or source.name
        final_name = sanitize_emoji_name(raw_name) if raw_name else "emote"
        if len(final_name) < 2 or len(final_name) > 32:
            raise ValueError("Invalid emote name length. Must be between 2 and 32 characters.")
        try:
            return await ctx.bot.rest.create_emoji(guild_id, name=final_name, image=source)
        except Exception:
            if hasattr(source, "url") and source.url:
                return await add_emoji_from_source(ctx, str(source.url), name=final_name)
            raise

    if isinstance(source, bytes):
        if not name:
            raise ValueError("An emote name must be provided for raw bytes.")
        final_name = sanitize_emoji_name(name)
        if len(final_name) < 2 or len(final_name) > 32:
            raise ValueError("Invalid emote name length. Must be between 2 and 32 characters.")
        return await ctx.bot.rest.create_emoji(guild_id, name=final_name, image=source)

    # 2. If source is link or attachment, validate name
    raw_name = name or "emote"
    final_name = sanitize_emoji_name(raw_name)
    if len(final_name) < 2 or len(final_name) > 32:
        raise ValueError("Invalid emote name length. Must be between 2 and 32 characters.")

    # 3. Handle Attachment
    if isinstance(source, hk.Attachment):
        is_animated = (
            source.filename.lower().endswith((".gif", ".webp"))
            or (hasattr(source, "media_type") and source.media_type in ["image/gif", "image/webp"])
        )
        img_bytes = await source.read()

        if is_animated:
            try:
                return await ctx.bot.rest.create_emoji(guild_id, name=final_name, image=img_bytes)
            except hk.BadRequestError as e:
                raise ValueError(
                    "Failed to add animated emote (Discord rejected the file: size may exceed 256KB or format is unsupported)."
                ) from e

        # Static image (type 1)
        if len(img_bytes) / (1024 * 256) > 1:
            if hasattr(ctx, "respond"):
                await ctx.respond("Image size possibly too large, attempting compression...")
            im = Image.open(io.BytesIO(img_bytes))
            im = ImageOps.contain(im, (128, 128), Image.Resampling.LANCZOS)
            new_pixels = io.BytesIO()
            im.save(new_pixels, format="PNG", optimize=True)
            img_bytes = new_pixels.getvalue()

        return await ctx.bot.rest.create_emoji(guild_id, name=final_name, image=img_bytes)

    # 4. Handle Link / URL
    if isinstance(source, str):
        if not check_if_url(source):
            raise ValueError("Invalid image url")

        if not check_if_known_emoji_provider(source):
            raise ValueError("Unknown Emote Provider")

        session = getattr(ctx.bot.d, "aio_session", None)
        if not session:
            raise ValueError("HTTP session is required to fetch image URLs.")

        image_type = await is_image(source, session)
        if not image_type:
            raise ValueError("Invalid image url")

        if image_type == 2:
            # Animated / GIF / WebP: try to add directly
            try:
                return await ctx.bot.rest.create_emoji(guild_id, name=final_name, image=source)
            except hk.BadRequestError as e:
                raise ValueError(
                    "Failed to add animated emote (Discord rejected the file: size may exceed 256KB or format is unsupported)."
                ) from e

        if image_type == 1:
            # Static image: check if compression needed
            async with session.get(source) as resp:
                img_bytes = await resp.read()

            if len(img_bytes) / (1024 * 256) > 1:
                if hasattr(ctx, "respond"):
                    await ctx.respond("Image size possibly too large, attempting compression...")
                im = Image.open(io.BytesIO(img_bytes))
                im = ImageOps.contain(im, (128, 128), Image.Resampling.LANCZOS)
                new_pixels = io.BytesIO()
                im.save(new_pixels, format="PNG", optimize=True)
                img_bytes = new_pixels.getvalue()

            return await ctx.bot.rest.create_emoji(guild_id, name=final_name, image=img_bytes)

    raise ValueError("Invalid emote source provided.")
