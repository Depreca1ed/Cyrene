from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import BaseCog, TimeConverter

if TYPE_CHECKING:
    import datetime

    from utils import Context


dt_param = commands.parameter(converter=TimeConverter, default=None)


class Actions(BaseCog):
    @commands.hybrid_command(name='ban', description='Bans a member from the server')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(
        self,
        ctx: Context,
        member: discord.Member | discord.User,
        duration: datetime.datetime | None = dt_param,  # noqa: ARG002
        *,
        delete_messages_days: commands.Range[int, 0, 7] = 0,
        reason: str | None = None,
    ) -> None:
        moderator = ctx.author
        if not ctx.guild or not isinstance(moderator, discord.Member):
            return

        if (ctx.guild.owner_id and ctx.guild.owner_id == member.id) or (
            isinstance(member, discord.Member) and member.top_role > moderator.top_role
        ):
            msg = 'You do not have the permissions to **ban** this user.'
            raise commands.BadArgument(msg)

        # TODO(Depreca1ed): Add functionality for registering mod action to db.

        await ctx.guild.ban(
            member,
            delete_message_days=delete_messages_days,
            reason=reason,
        )
