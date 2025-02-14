"""
This file was sourced from [RoboDanny](https://github.com/Rapptz/RoboDanny).

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
# This copy of launcher.py has been modified very deeply but still sources back to RoboDanny's

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import asyncpg
import discord

from config import DATABASE_CRED, TOKEN
from utils import Mafuyu

if TYPE_CHECKING:
    from collections.abc import Generator


@contextlib.contextmanager
def setup_logging() -> Generator[Any, Any, Any]:
    discord.utils.setup_logging()

    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    yield


async def create_bot_pool() -> asyncpg.Pool[asyncpg.Record]:
    pool = await asyncpg.create_pool(DATABASE_CRED)

    if not pool or pool.is_closing():
        msg = 'Failed to create a pool.'
        raise RuntimeError(msg)

    with Path('schema.sql').open(encoding='utf-8') as file:  # noqa: ASYNC230
        await pool.execute(file.read())

    return pool


if __name__ == '__main__':
    with setup_logging():

        async def run_bot() -> None:
            pool = await create_bot_pool()
            allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=False)
            intents = discord.Intents.all()
            session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))

            extensions = [
                'extensions.animanga',
                'extensions.internals',
                'extensions.meta',
            ]

            async with Mafuyu(
                extensions=extensions,
                allowed_mentions=allowed_mentions,
                intents=intents,
                session=session,
            ) as bot:
                bot.pool = pool
                await bot.start(TOKEN)

        asyncio.run(run_bot())
