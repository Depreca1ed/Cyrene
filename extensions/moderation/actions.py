from __future__ import annotations

import asyncio
import contextlib
import datetime
import enum
from typing import TYPE_CHECKING

import asyncpg
import discord
from asyncpg import Record
from discord.ext import commands

from utils import BaseCog, BotEmojis, TimeConverter

if TYPE_CHECKING:
    from utils import Context, Mafuyu


dt_param = commands.parameter(converter=TimeConverter, default=None)


class ModerationAction(enum.IntEnum):
    UNBAN = 1
    UNTIMEOUT = 2


class Actions(BaseCog):
    def __init__(self, bot: Mafuyu) -> None:
        super().__init__(bot)
        self._current_timer: datetime.datetime | None = (
            None  # This is the timestamp fo the latest punishment to be dispatched
        )
        self._have_data = asyncio.Event()
        self._task = self.bot.loop.create_task(self.dispatch_punishment_removal())

    async def get_active_punishment(self) -> Record | None:
        query = """
            SELECT * FROM ModerationActions
            WHERE until < (CURRENT_TIMESTAMP + $1::interval)
            ORDER BY until
            LIMIT 1;
        """

        return await self.bot.pool.fetchrow(query, datetime.timedelta(days=40))

    async def wait_for_active_punishments(self) -> Record:
        p = await self.get_active_punishment()
        if p is not None:
            self._have_data.set()
            return p

        self._have_data.clear()
        self._current_timer = None
        await self._have_data.wait()

        return await self.get_active_punishment()  # pyright: ignore[reportReturnType]

    async def dispatch_punishment_removal(self) -> None:
        try:
            while not self.bot.is_closed():
                p = await self.wait_for_active_punishments()
                self._current_timer = p['until']
                expire: datetime.datetime = p['until']
                now = datetime.datetime.now()

                if expire >= now:
                    to_sleep = (expire - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_punishment_remove(
                    p['action_type'],
                    p['target'],
                    p['guild_id'],
                )
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_punishment_removal())

    async def call_punishment_remove(self, action_type: ModerationAction, guild_id: int, target: int) -> None:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        if action_type == ModerationAction.UNBAN:
            await guild.unban(
                discord.Object(id=target),
                reason='Ban duration has expired.',
            )

    async def handle_ban_with_duration(
        self,
        guild: discord.Guild,
        member: discord.Member | discord.User,
        *,
        duration: datetime.datetime,
    ) -> None:
        now = datetime.datetime.now()
        dur = duration - now

        if dur.total_seconds() < 30:
            await asyncio.sleep(dur.seconds)
            await self.call_punishment_remove(ModerationAction.UNBAN, guild.id, member.id)
            return

        await self.bot.pool.execute(
            """
            INSERT INTO
                ModerationActions (action_type, target, guild_id, until)
            VALUES
                ($1, $2, $3, $4)
                """,
            ModerationAction.UNBAN,
            member.id,
            guild.id,
            duration,
        )
        if dur.total_seconds() <= (86400 * 40):  # 40 days
            self._have_data.set()

        if self._current_timer and duration < self._current_timer:
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_punishment_removal())

    @commands.hybrid_command(name='ban', description='Bans a member from the server')
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_guild_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(
        self,
        ctx: Context,
        member: discord.Member | discord.User,
        *,
        duration: datetime.datetime | None = dt_param,
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

        await ctx.guild.ban(
            member,
            delete_message_days=delete_messages_days,
            reason=reason,
        )

        if duration:
            await self.handle_ban_with_duration(ctx.guild, member, duration=duration)

        with contextlib.suppress(discord.HTTPException):
            await ctx.message.add_reaction(BotEmojis.GREEN_TICK)

    @commands.hybrid_command(name='unban', description='Unbans a member from the server')
    @commands.guild_only()
    async def unban(
        self,
        ctx: Context,
        member: discord.Member | discord.User,
        *,
        reason: str | None = None,
    ) -> None:
        if not ctx.guild:
            return

        await ctx.guild.unban(member, reason=reason)
