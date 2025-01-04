from __future__ import annotations

import datetime

import discord  # noqa: TCH002
from discord.ext import commands

from utils import AlreadyBlacklistedError, BaseCog, Context, NotBlacklistedError, better_string

WHITELISTED_GUILDS = [1219060126967664754, 774561547930304536]


class Developer(BaseCog):
    @commands.command(name='reload', aliases=['re'], hidden=True)
    async def reload_cogs(self, ctx: Context) -> None:
        exts = self.bot.initial_extensions
        messages: list[str] = []

        for ext in exts:
            try:
                await self.bot.reload_extension(str(ext))
            except commands.ExtensionError as error:
                messages.append(f'Failed to reload {ext}\n```py{error}```')
            else:
                messages.append(f'Reloaded {ext}')

        await ctx.send(content=better_string(messages, seperator='\n'))

    @commands.group(
        name='blacklist',
        aliases=['bl'],
        invoke_without_command=True,
        help='The command which handles bot blacklists',
    )
    async def blacklist_cmd(self, ctx: Context) -> None:
        bl = self.bot.blacklist

        bl_guild_count = len([entry for entry in bl.blacklist_cache if bl.blacklist_cache[entry].blacklist_type == 'guild'])
        bl_user_count = len([entry for entry in bl.blacklist_cache if bl.blacklist_cache[entry].blacklist_type == 'user'])

        content = f'Currently, `{bl_guild_count}` servers and `{bl_user_count}` users are blacklisted.'
        await ctx.reply(content=content)

    async def _handle_datetime_argument(self, ctx: Context, dt: str) -> None | datetime.datetime:
        suffixes = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'mo': 2592000,
            'y': 2592000 * 12,
        }

        if dt[-1:] not in suffixes:
            await ctx.reply(f"{ctx.author.mention}, i can't understand the time you provided.")
            return None
        parsed = suffixes[dt[-1:]]
        c = int(dt[:-1]) if dt[-2:] != 'mo' else int(dt[-2:])
        final = c * parsed
        return datetime.datetime.now() + datetime.timedelta(seconds=final)

    @blacklist_cmd.command(name='add', help='Add a user to the blacklist')
    async def blacklist_add(
        self,
        ctx: Context,
        user: discord.User | discord.Member | discord.Guild,
        until: str | None,
        *,
        reason: str = 'No reason provided',
    ) -> None:
        bl_until = None
        if until:
            bl_until = await self._handle_datetime_argument(ctx, until)
            if not bl_until:
                return

        try:
            await self.bot.blacklist.add(user, lasts_until=bl_until, reason=reason)

        except AlreadyBlacklistedError as err:
            content = str(err)
            await ctx.reply(content)

        await ctx.message.add_reaction(self.bot.bot_emojis['green_tick'])
        return

    @blacklist_cmd.command(name='remove', help='Remove a user from blacklist')
    async def blacklist_remove(self, ctx: Context, user: discord.User | discord.Member | discord.Guild) -> None:
        try:
            await self.bot.blacklist.remove(user)

        except NotBlacklistedError as err:
            content = str(err)
            await ctx.reply(content)
            return

        await ctx.message.add_reaction(self.bot.bot_emojis['green_tick'])
