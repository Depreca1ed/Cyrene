from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from discord import Emoji, PartialEmoji

    from utilities.bases.bot import Elysia

__all__ = ('ElyCog',)


class ElyCog(commands.Cog):
    bot: Elysia
    emoji: str | PartialEmoji | Emoji | None

    def __init__(
        self,
        bot: Elysia,
        emoji: str | PartialEmoji | Emoji | None = None,
    ) -> None:
        self.bot = bot
        self.emoji = emoji
        super().__init__()
