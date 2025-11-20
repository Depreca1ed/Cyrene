from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import asyncpg
import click
import discord
from discord.ext import commands

from config import DATABASE_CRED, TEST_TOKEN, TOKEN
from utilities.bases.bot import Cyrene

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


async def _callable_prefix(bot: Cyrene, message: discord.Message) -> list[str]:
    prefixes = commands.when_mentioned(bot, message)

    prefixes.extend(bot.get_prefixes(message.guild))

    return prefixes


@click.command()
@click.option('--production', is_flag=True)
def run(*, production: bool) -> None:
    token = TOKEN if production else TEST_TOKEN
    with setup_logging():

        async def run_bot(token: str) -> None:
            pool = await create_bot_pool()
            allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=False)
            intents = discord.Intents.all()
            session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))

            extensions = [
                'extensions.animanga',
                'extensions.internals',
                'extensions.meta',
                'extensions.utility',
                'extensions.realmsphere',
            ]

            async with Cyrene(
                command_prefix=_callable_prefix,
                extensions=extensions,
                allowed_mentions=allowed_mentions,
                intents=intents,
                session=session,
            ) as bot:
                bot.pool = pool
                await bot.start(token)

        asyncio.run(run_bot(token=token))


if __name__ == '__main__':
    run()
