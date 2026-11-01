"""One-off: copy user_links from the SQLite akane_db.db into Postgres akanebot.users

Usage (production): docker compose run --rm akane-bot python scripts/migrate_user_links.py
Re-running overwrites the Postgres rows with the SQLite ones, so only run it before the bot writes to Postgres.
"""

import asyncio
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from utils import user_links

load_dotenv()


async def migrate(sqlite_path: str) -> None:
    with sqlite3.connect(sqlite_path) as con:
        rows = con.execute(
            "SELECT discord_id, anilist_name, anilist_id, prompt_after FROM user_links"
        ).fetchall()
    records = [
        {"id": discord_id, "name": name, "anilist_id": anilist_id, "prompt_after": prompt_after}
        for discord_id, name, anilist_id, prompt_after in rows
    ]

    engine = create_async_engine(os.getenv("DATABASE_URL"))
    pg = async_sessionmaker(engine, expire_on_commit=False)
    try:
        await user_links.create_table(pg)
        async with pg() as session, session.begin():
            if records:
                await session.execute(
                    text(
                        """
                        INSERT INTO akanebot.users (discord_id, anilist_name, anilist_id, prompt_after)
                        VALUES (:id, :name, :anilist_id, :prompt_after)
                        ON CONFLICT (discord_id) DO UPDATE
                        SET anilist_name = EXCLUDED.anilist_name, anilist_id = EXCLUDED.anilist_id,
                            prompt_after = EXCLUDED.prompt_after, updated_at = now()
                        """
                    ),
                    records,
                )
            total = (await session.execute(text("SELECT count(*) FROM akanebot.users"))).scalar()
    finally:
        await engine.dispose()
    print(f"Copied {len(records)} rows from {sqlite_path}; akanebot.users now has {total} rows")


if __name__ == "__main__":
    asyncio.run(migrate(sys.argv[1] if len(sys.argv) > 1 else "akane_db.db"))
