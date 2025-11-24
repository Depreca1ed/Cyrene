from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from discord import Emoji, PartialEmoji

    from utilities.bases.bot import Cyrene


class CyCog(commands.Cog):
    bot: Cyrene
    emoji: str | PartialEmoji | Emoji | None

    def __init__(
        self,
        bot: Cyrene,
        emoji: str | PartialEmoji | Emoji | None = None,
    ) -> None:
        self.bot = bot
        self.emoji = emoji
        super().__init__()
