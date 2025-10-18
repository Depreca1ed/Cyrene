from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from utilities.bases.cog import ElyCog
from utilities.constants import BotEmojis
from utilities.functions import format_tb

if TYPE_CHECKING:
    from discord import Message

    from utilities.bases.context import ElyContext


class Developer(ElyCog):
    @commands.command(name='reload', aliases=['re'], hidden=True)
    async def reload_cogs(self, ctx: ElyContext) -> None | Message:
        try:
            await self.bot.reload_extensions(self.bot.initial_extensions)
        except commands.ExtensionError as error:
            return await ctx.reply(format_tb(error))
        else:
            return await ctx.message.add_reaction(BotEmojis.GREEN_TICK)
