"""Dev mode: run the bot and hot-reload its plugins whenever a Python file changes.

    python dev.py

Changes to extensions/ or utils/ reload every extension in place and re-sync slash
commands; the gateway connection and bot.d state are kept. Changes to bot.py or the
modules whose objects live in bot.d (CORE_MODULES) can't be reloaded safely, so those
restart the process instead.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import hikari as hk
from lightbulb.ext import tasks
from watchfiles import PythonFilter, awatch

from bot import bot

ROOT = Path(__file__).resolve().parent
IGNORE = ["tests", "hakushin", "test.py", "dev.py"]

# bot.d holds instances of these (and they raise these errors), so a reloaded copy would
# no longer match the live objects, e.g. `except AniListError` missing the old client's
CORE_MODULES = {"bot", "utils.anilist_client", "utils.mal_client", "utils.errors"}

log = logging.getLogger("dev")
# watchfiles debug-logs every raw change, including writes to the log file itself,
# so at DEBUG it feeds itself and floods the log
logging.getLogger("watchfiles").setLevel(logging.INFO)
EXTENSIONS = list(bot.extensions)  # loaded by bot.py on import
restart = False


def module_name(path: str) -> str:
    rel = Path(path).resolve().relative_to(ROOT).with_suffix("")
    parts = rel.parts[:-1] if rel.name == "__init__" else rel.parts
    return ".".join(parts)


async def reload_plugins(changed: set[str]) -> None:
    # Unload everything before loading anything: extensions share state across modules
    # (vn attaches subcommands to adata's /lookup group), so reloading one at a time
    # would re-add subcommands to the old group and fail
    for ext in list(bot.extensions):
        # auto_start tasks start on import, so stop the old copies or they'd pile up per reload
        for obj in vars(sys.modules[ext]).values():
            if isinstance(obj, tasks.Task) and obj.is_running:
                obj.cancel()
        try:
            bot.unload_extensions(ext)
        except Exception as e:
            log.error(f"Failed to unload {ext}: {e!r}")

    # drop cached modules so everything is re-imported fresh (core ones stay shared)
    for name in [m for m in sys.modules if m.startswith(("utils.", "extensions.")) and m not in CORE_MODULES]:
        del sys.modules[name]
        # the package keeps the old module as an attribute, which `from utils import x` would return
        parent, _, child = name.rpartition(".")
        if parent in sys.modules:
            vars(sys.modules[parent]).pop(child, None)

    failed = []
    for ext in EXTENSIONS:  # the startup list, so a broken extension is retried next save
        try:
            bot.load_extensions(ext)
        except Exception as e:
            failed.append(ext)
            log.error(f"Failed to load {ext}: {e!r}")

    await bot.sync_application_commands()
    failures = f" ({len(failed)} failed: {', '.join(failed)})" if failed else ""
    log.info(
        f"Reloaded {len(EXTENSIONS) - len(failed)} extension(s) after changes to "
        f"{', '.join(sorted(changed))}{failures}"
    )


async def watch() -> None:
    global restart
    async for changes in awatch(ROOT, watch_filter=PythonFilter(ignore_paths=IGNORE)):
        changed = {module_name(path) for _, path in changes}
        if changed & CORE_MODULES:
            log.warning(f"Core module changed ({', '.join(sorted(changed & CORE_MODULES))}), restarting")
            restart = True
            await bot.close()
            return
        await reload_plugins(changed)


@bot.listen(hk.StartedEvent)
async def start_watcher(_: hk.StartedEvent) -> None:
    asyncio.create_task(watch())


if __name__ == "__main__":
    import uvloop

    uvloop.install()
    bot.run(
        status=hk.Status.IDLE,
        activity=hk.Activity(name="『Idol』 | -help", type=hk.ActivityType.LISTENING),
    )
    if restart:
        os.execv(sys.executable, [sys.executable, *sys.argv])
