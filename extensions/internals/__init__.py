from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utilities.bases.bot import Mafuyu
    from utilities.bases.context import MafuContext
import contextlib

import discord
from discord.ext import commands

from .blacklist import Blacklist
from .dev import Developer
from .error_handler import ErrorHandler
from .guild import Guild


class Internals(Blacklist, Developer, ErrorHandler, Guild, name='Developer'):
    @discord.utils.copy_doc(commands.Cog.cog_check)
    async def cog_check(self, ctx: MafuContext) -> bool:
        if await self.bot.is_owner(ctx.author):
            return True
        msg = 'You do not own this bot.'
        raise commands.NotOwner(msg)

    @commands.Cog.listener('on_message_edit')
    async def edit_mechanic(self, _: discord.Message, after: discord.Message) -> None:
        if await self.bot.is_owner(after.author):
            await self.bot.process_commands(after)

    @commands.Cog.listener('on_reaction_add')
    async def delete_message(self, reaction: discord.Reaction, _: discord.Member | discord.User) -> None:
        if reaction.emoji and reaction.emoji == '🗑️' and reaction.message.author.id == self.bot.user.id:
            with contextlib.suppress(discord.HTTPException):
                await reaction.message.delete()


async def setup(bot: Mafuyu) -> None:
    await bot.add_cog(Internals(bot))
