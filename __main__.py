"""
This file was sourced from [RoboDanny](https://github.com/Rapptz/RoboDanny).

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

import discord

from bot import Mafuyu

if TYPE_CHECKING:
    from collections.abc import Generator


class RemoveNoise(logging.Filter):
    def __init__(self) -> None:
        super().__init__(name='discord.state')

    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.levelname == 'WARNING' and 'referencing an unknown' in record.msg)


@contextlib.contextmanager
def setup_logging() -> Generator[Any, Any, Any]:
    discord.utils.setup_logging()
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.state').addFilter(RemoveNoise())
    yield


if __name__ == '__main__':
    with setup_logging():

        async def run_bot() -> None:
            async with Mafuyu() as bot:
                await bot.start(bot.token)

        asyncio.run(run_bot())
