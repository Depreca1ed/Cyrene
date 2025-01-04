from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Self

import discord

from .errors import (
    AlreadyBlacklistedError,
    NotBlacklistedError,
)
from .types import BlacklistBase

if TYPE_CHECKING:
    from bot import Mafuyu

    from .context import Context

__all__ = ('Blacklist',)


class Blacklist:
    blacklist_cache: dict[int, BlacklistBase]

    def __init__(self, bot: Mafuyu, blacklist_cache: dict[int, BlacklistBase]) -> None:
        self.blacklist_cache = blacklist_cache

        self.bot = bot
        self.bot.check_once(self.check)

        self._command_attempts: dict[int, int] = {}
        super().__init__()

    @classmethod
    async def setup(cls, bot: Mafuyu) -> Self:
        entries = await bot.pool.fetch("""SELECT * FROM Blacklists""")

        blacklist_cache: dict[int, BlacklistBase] = {}

        for entry in entries:
            blacklist_cache[entry['snowflake']] = BlacklistBase(
                reason=entry['reason'],
                lasts_until=entry['lasts_until'],
                blacklist_type=entry['blacklist_type'],
            )

        return cls(bot, blacklist_cache)

    async def handle_user_blacklist(self, ctx: Context, user: discord.User | discord.Member, data: BlacklistBase) -> None:
        """
        Handle the actions to be done when the bot comes across a blacklisted user.

        Parameters
        ----------
        ctx : Context
            The commands.Context from the check
        user : discord.User | discord.Member
            The blacklisted User
        data : BlacklistBase
            The data of the blacklisted users i.e. reason, lasts_until & blacklist_type

        """
        timestamp_wording = self._timestamp_wording(data.lasts_until)
        content = (
            f'{user.mention}, you are blacklisted from using {ctx.bot.user} for `{data.reason}` {timestamp_wording}. '
            f'If you wish to appeal this blacklist, please join the [Support Server]( {self.bot.support_invite} ).'
        )

        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.channel.send(content)
            return

        attempt_check = self._command_attempts.get(user.id)

        if not attempt_check:
            self._command_attempts[user.id] = 1
            return

        if attempt_check >= 5:
            await ctx.channel.send(content)
            del self._command_attempts[user.id]
            return

        self._command_attempts[user.id] += 1

        return

    async def handle_guild_blacklist(self, ctx: Context | None, guild: discord.Guild, data: BlacklistBase) -> None:
        """
        Handle the actions to be done when the bot comes across a blacklisted guild.

        This function is also used in the on_guild_join event thus the optional context argument.


        Parameters
        ----------
        ctx : Context | None
            The commands.Context from the check. Will be optional when used in the event.
        guild : discord.Guild
            The blacklisted Guild
        data : BlacklistBase
            The data of the blacklisted users i.e. reason, lasts_until & blacklist_type

        """
        channel = (
            ctx.channel
            if ctx
            else discord.utils.find(
                lambda ch: (ch.guild.system_channel or 'general' in ch.name.lower())  # The channel to choose
                and ch.permissions_for(guild.me).send_messages is True,  # The check for if we can send message
                guild.text_channels,
            )
        )

        timestamp_wording = self._timestamp_wording(data.lasts_until)
        content = (
            f'`{guild}` is blacklisted from using this bot for `{data.reason}` {timestamp_wording}.'
            f'If you wish to appeal this blacklist, please join the [Support Server]( {self.bot.support_invite} ).'
        )

        if channel:
            await channel.send(content=content)

    async def _pre_check(self, snowflake: discord.User | discord.Member | discord.Guild, data: BlacklistBase) -> bool:
        """
        Check(not to be confused with command check) to make sure user is actually still blacklisted.

        Parameters
        ----------
        snowflake : discord.User | discord.Member | discord.Guild
            The snowflake being checked
        data : BlacklistBase
            Blacklist data of the snowflake

        Returns
        -------
        bool
            If user is still blacklisted

        """
        if data.lasts_until and datetime.datetime.now() > data.lasts_until:
            await self.remove(snowflake)
            return True
        return False

    async def check(self, ctx: Context) -> bool:
        """
        Blacklist check ran every command.

        Parameters
        ----------
        ctx : Context
            The commands.Context from the check

        Returns
        -------
        bool
            If the command should be run

        """
        if data := self.is_blacklisted(ctx.author):
            if not await self._pre_check(ctx.author, data):
                return True
            await self.handle_user_blacklist(ctx, ctx.author, data)
            return False

        if ctx.guild and (data := self.is_blacklisted(ctx.guild)):
            if not await self._pre_check(ctx.guild, data):
                return True
            await self.handle_guild_blacklist(ctx, ctx.guild, data)
            return False

        return True

    def is_blacklisted(self, snowflake: discord.User | discord.Member | discord.Guild) -> BlacklistBase | None:
        """
        Get item function which gets the item from the cache.

        Parameters
        ----------
        snowflake : discord.User | discord.Member | discord.Guild
            The snowflake item being checked

        Returns
        -------
        BlacklistBase | None
            Blacklist data of the snowflake if any

        """
        return self.blacklist_cache.get(snowflake.id, None)

    async def add(
        self,
        snowflake: discord.User | discord.Member | discord.Guild,
        *,
        reason: str,
        lasts_until: datetime.datetime | None = None,
    ) -> dict[int, BlacklistBase]:
        """
        Add an entry to the blacklist.

        This adds the entry to the database as well as cache

        Parameters
        ----------
        snowflake : discord.User | discord.Member | discord.Guild
            The snowflake being blacklisted
        reason : str, optional
            The reason for the blacklist, by default 'No reason provided'
        lasts_until : datetime.datetime | None, optional
            For how long the snowflake is blacklisted for, by default None

        Returns
        -------
        dict[int, BlacklistBase]
            Returns a dict of the snowflake and the data as stored in the cache

        Raises
        ------
        AlreadyBlacklistedError
            Raised when snowflake being blacklisted is already blacklisted.
            This is handled by the command executing this function

        """
        entry = self.is_blacklisted(snowflake)

        if entry:
            check = await self._pre_check(snowflake, entry)
            if check:
                raise AlreadyBlacklistedError(snowflake, reason=entry.reason, until=entry.lasts_until)
        blacklist_type = 'user' if isinstance(snowflake, discord.User | discord.Member) else 'guild'

        await self.bot.pool.execute(
            """INSERT INTO
                    Blacklists (snowflake, reason, lasts_until, blacklist_type)
               VALUES
                    ($1, $2, $3, $4);""",
            snowflake.id,
            reason,
            lasts_until,
            blacklist_type,
        )

        self.blacklist_cache[snowflake.id] = BlacklistBase(
            reason=reason,
            lasts_until=lasts_until,
            blacklist_type=blacklist_type,
        )
        return {snowflake.id: self.blacklist_cache[snowflake.id]}

    async def remove(self, snowflake: discord.User | discord.Member | discord.Guild) -> dict[int, BlacklistBase]:
        """
        Remove an entry from the blacklist.

        This removes the entry from the database as well as cache

        Parameters
        ----------
        snowflake : discord.User | discord.Member | discord.Guild
            The snowflake being removed from blacklist

        Returns
        -------
        dict[int, BlacklistBase]
            A dict of the snowflake and the data as was in the cache beforehand

        Raises
        ------
        NotBlacklistedError
            Raised when the snowflake is not blacklisted to begin with

        """
        if not self.is_blacklisted(snowflake):
            raise NotBlacklistedError(snowflake)

        await self.bot.pool.execute(
            """DELETE FROM Blacklists WHERE snowflake = $1""",
            snowflake.id,
        )

        item_removed = self.blacklist_cache.pop(snowflake.id)
        return {snowflake.id: item_removed}

    def _timestamp_wording(self, dt: datetime.datetime | None) -> str:
        return f'until {discord.utils.format_dt(dt, "f")}' if dt else 'permanently'

    def __repr__(self) -> str:
        return str(self.blacklist_cache)
