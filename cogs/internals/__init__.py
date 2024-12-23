from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bot import DeBot
    from utils import DeContext
import contextlib

import discord
from discord.ext import commands

from .dev import Developer
from .error_handler import ErrorHandler


class Internals(Developer, ErrorHandler, name='Internals'):
    @discord.utils.copy_doc(commands.Cog.cog_check)
    async def cog_check(self, ctx: DeContext) -> bool:
        return await self.bot.is_owner(ctx.author)

    @commands.Cog.listener('on_message_edit')
    async def edit_mechanic(self, _: discord.Message, after: discord.Message) -> None:
        if await self.bot.is_owner(after.author):
            await self.bot.process_commands(after)

    @commands.Cog.listener('on_reaction_add')
    async def delete_message(self, reaction: discord.Reaction, user: discord.Member | discord.User) -> None:
        if (
            await self.bot.is_owner(user)
            and reaction.emoji
            and reaction.emoji == '🗑️'
            and reaction.message.author.id == self.bot.user.id
        ):
            with contextlib.suppress(discord.HTTPException):
                await reaction.message.delete()

    @commands.Cog.listener('on_dbl_vote')
    async def dbl_vote_handler(self, data: dict[Any, Any]) -> None:
        await self.bot.logger_webhook.send(content=str(data))


async def setup(bot: DeBot) -> None:
    await bot.add_cog(Internals(bot))
