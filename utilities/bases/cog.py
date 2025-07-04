from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from discord import Emoji, PartialEmoji

    from utilities.bases.bot import Mafuyu

__all__ = ('MafuCog',)


class MafuCog(commands.Cog):
    bot: Mafuyu
    emoji: str | PartialEmoji | Emoji | None

    def __init__(
        self,
        bot: Mafuyu,
        emoji: str | PartialEmoji | Emoji | None = None,
    ) -> None:
        self.bot = bot
        self.emoji = emoji
        super().__init__()
