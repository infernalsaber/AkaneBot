"""Discord user -> AniList user links, plus the "save your username?" prompt"""

import sqlite3
import time

import hikari as hk
import miru

from utils.errors import AniListError
from utils.views import AuthorView

SNOOZE_SECONDS = 10 * 24 * 60 * 60  # "Not now" waits 10 days before asking again
NEVER = -1  # prompt_after value for "Don't ask again"


def create_table(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS user_links (
            discord_id   INTEGER PRIMARY KEY,
            anilist_name TEXT,
            anilist_id   INTEGER,
            prompt_after INTEGER  -- unix ts; NULL = can ask, -1 = never ask
        )
        """
    )
    con.commit()


def get_link(con: sqlite3.Connection, discord_id: int) -> int | None:
    """The saved AniList id, or None"""
    row = con.execute(
        "SELECT anilist_id FROM user_links WHERE discord_id = ? AND anilist_name IS NOT NULL",
        (discord_id,),
    ).fetchone()
    return row[0] if row else None


def set_link(con: sqlite3.Connection, discord_id: int, name: str, anilist_id: int) -> None:
    con.execute(
        """
        INSERT INTO user_links (discord_id, anilist_name, anilist_id) VALUES (?, ?, ?)
        ON CONFLICT(discord_id) DO UPDATE
        SET anilist_name = excluded.anilist_name, anilist_id = excluded.anilist_id
        """,
        (discord_id, name, anilist_id),
    )
    con.commit()


def remove_link(con: sqlite3.Connection, discord_id: int) -> bool:
    """Unset the saved username. False if there was nothing saved."""
    cur = con.execute(
        "UPDATE user_links SET anilist_name = NULL, anilist_id = NULL "
        "WHERE discord_id = ? AND anilist_name IS NOT NULL",
        (discord_id,),
    )
    con.commit()
    return cur.rowcount > 0


def set_prompt_after(con: sqlite3.Connection, discord_id: int, value: int) -> None:
    con.execute(
        """
        INSERT INTO user_links (discord_id, prompt_after) VALUES (?, ?)
        ON CONFLICT(discord_id) DO UPDATE SET prompt_after = excluded.prompt_after
        """,
        (discord_id, value),
    )
    con.commit()


def should_prompt(con: sqlite3.Connection, discord_id: int) -> bool:
    """True if the user has no saved username and hasn't snoozed or declined the prompt"""
    row = con.execute(
        "SELECT anilist_name, prompt_after FROM user_links WHERE discord_id = ?",
        (discord_id,),
    ).fetchone()
    if not row:
        return True
    name, prompt_after = row
    if name:
        return False
    return prompt_after is None or (prompt_after != NEVER and prompt_after <= time.time())


async def resolve_user(client, name: str) -> dict | None:
    """Look up an AniList user by name -> {"id", "name"}

    None if the user doesn't exist. Raises AniListError if AniList is unreachable.
    """
    if not getattr(client, "is_available", True):
        raise AniListError("AniList is unavailable")
    try:
        data = await client.query("query ($name: String) { User(name: $name) { id name } }", {"name": name})
    except AniListError:
        if not getattr(client, "is_available", True):
            raise
        return None  # GraphQL "not found" error
    return data.get("User")


class LinkModal(miru.Modal):
    """Asks for the AniList username and saves it"""

    def __init__(self, prompt: "LinkPromptView") -> None:
        super().__init__(title="Save your AniList username")
        self.prompt = prompt
        self.username = miru.TextInput(
            label="AniList username",
            value=prompt.prefill,
            required=True,
            max_length=20,
        )
        self.add_item(self.username)

    async def callback(self, ctx: miru.ModalContext) -> None:
        name = (self.username.value or "").strip()
        try:
            user = await resolve_user(self.prompt.client, name)
        except AniListError:
            return await ctx.respond(
                "AniList is down right now, try again later with `-um set <name>`.",
                flags=hk.MessageFlag.EPHEMERAL,
            )
        if not user:
            return await ctx.respond(
                f"Couldn't find an AniList user called `{name}` 😵",
                flags=hk.MessageFlag.EPHEMERAL,
            )
        set_link(self.prompt.con, ctx.user.id, user["name"], user["id"])
        await self.prompt.finish(
            ctx,
            f"Saved ✅ You're linked to **{user['name']}**. Use `-user` on its own to see your profile.",
        )


class LinkPromptView(AuthorView):
    """Add username / Not now / Don't ask again

    Prefix commands can't send ephemeral messages, so the prompt is a normal
    message that deletes itself after a choice or on timeout. Replies to the
    clicks are ephemeral.
    """

    def __init__(self, user_id: hk.Snowflake, con, client, prefill: str) -> None:
        super().__init__(timeout=60, user_id=user_id, clean_items=False)
        self.con = con
        self.client = client
        self.prefill = prefill

    async def delete_message(self) -> None:
        if self.message:
            try:
                await self.message.delete()
            except hk.HTTPError:
                pass

    async def finish(self, ctx: miru.Context, text: str) -> None:
        self.stop()
        await ctx.respond(text, flags=hk.MessageFlag.EPHEMERAL)
        await self.delete_message()

    # The view keeps running while the modal is open, so a cancelled modal
    # leaves the buttons usable. The modal stops the view on success.
    @miru.button(label="Add username", emoji="📝", style=hk.ButtonStyle.PRIMARY)
    async def add(self, _: miru.Button, ctx: miru.ViewContext) -> None:
        await ctx.respond_with_modal(LinkModal(self))

    @miru.button(label="Not now", emoji="⏲️", style=hk.ButtonStyle.SECONDARY)
    async def later(self, _: miru.Button, ctx: miru.ViewContext) -> None:
        set_prompt_after(self.con, ctx.user.id, int(time.time()) + SNOOZE_SECONDS)
        await self.finish(ctx, "Okay, I'll ask again in a while. You can also use `-um set <name>`.")

    @miru.button(label="Don't ask again", emoji="🚫", style=hk.ButtonStyle.DANGER)
    async def never(self, _: miru.Button, ctx: miru.ViewContext) -> None:
        set_prompt_after(self.con, ctx.user.id, NEVER)
        await self.finish(ctx, "Got it, I won't ask again. You can still use `-um set <name>`.")

    async def on_timeout(self) -> None:
        await self.delete_message()
