from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from bot import Mafuyu

__all__ = ('BaseCog',)


class BaseCog(commands.Cog):
    bot: Mafuyu

    def __init__(self, bot: Mafuyu) -> None:
        self.bot = bot
        super().__init__()
