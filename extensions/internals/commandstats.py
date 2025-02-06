from __future__ import annotations

import operator

import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, Context, Embed
from utils.helper_functions import better_string


class CommandStats(BaseCog):
    @commands.Cog.listener('on_command_completion')
    async def command_comp_register(self, ctx: Context) -> None:
        if not ctx.command:
            return
        command_name = ctx.command.qualified_name
        await ctx.bot.pool.execute(
            """
                    INSERT INTO
                        CommandStats (usage_count, command_name, user_id, channel_id, guild_id)
                    VALUES
                        (1, $1, $2, $3, $4)
                    ON CONFLICT(command_name, user_id, channel_id, guild_id) DO
                    UPDATE
                    SET
                        usage_count = CommandStats.usage_count + 1
                    """,
            command_name,
            ctx.author.id,
            ctx.channel.id if ctx.channel.type != discord.ChannelType.private else 0,
            ctx.guild.id if ctx.guild else 0,
        )

    async def handle_user(self, ctx: Context, user: discord.User | discord.Member, guild: discord.Guild | None) -> None:
        data = await self.bot.pool.fetch(
            """SELECT usage_count, command_name, guild_id FROM CommandStats WHERE user_id = $1""",
            user.id,
        )

        data_parsed = sorted(
            [(int(d['usage_count']), str(d['command_name'])) for d in data][:5],
            key=operator.itemgetter(0),
            reverse=True,
        )

        # So i have been wondering... what am i doing...

        sorted_commands: dict[str, int] = {}
        for cmd in data_parsed:
            if not sorted_commands.get(cmd[1]):
                sorted_commands[cmd[1]] = cmd[0]
                continue
            sorted_commands[cmd[1]] += cmd[0]

        embed = Embed(title=f'Command stats for {user}')
        embed.description = (
            f"> **{user}** has used the bot's commands `{sum(sorted_commands[d] for d in sorted_commands)}` times"
        )

        embed.add_field(
            name='Most used commands:',
            value=better_string(
                [f'{list(sorted_commands.keys()).index(d)}. {d} (`{sorted_commands[d]}` times)' for d in sorted_commands],
                seperator='\n',
            ),
        )

        embed.set_author(name=user, icon_url=user.display_avatar.url)

        if guild:
            sorted_guild_commands = sorted(
                [
                    (int(d['usage_count']), str(d['command_name']))
                    for d in data
                    if d['guild_id'] and d['guild_id'] == guild.id
                ][:5],
                key=operator.itemgetter(0),
                reverse=True,
            )
            if not sorted_guild_commands:
                await ctx.reply(embed=embed)
            glisting = [
                f"> **{user}** has used the bot's commands `{sum(_[0] for _ in sorted_guild_commands)}` times in {guild}\n"
            ]
            glisting.append(f'**Most used commands in {guild}**:')
            glisting.extend([f'{_}. {d[1]} (`{d[0]}` times)' for _, d in enumerate(sorted_guild_commands)])
            embed.add_field(name=f'Command stats inside {guild}', value=better_string(glisting, seperator='\n'))

        await ctx.reply(embed=embed)

    async def handle_channel(self, ctx: Context, channel: discord.abc.GuildChannel) -> None:
        data = await self.bot.pool.fetch(
            """SELECT usage_count, command_name FROM CommandStats WHERE channel_id = $1""",
            channel.id,
        )

        data_parsed = sorted(
            [(int(d['usage_count']), str(d['command_name'])) for d in data],
            key=operator.itemgetter(0),
            reverse=True,
        )
        sorted_commands: dict[str, int] = {}
        for cmd in data_parsed:
            if not sorted_commands.get(cmd[1]):
                sorted_commands[cmd[1]] = cmd[0]
                continue
            sorted_commands[cmd[1]] += cmd[0]
        embed = Embed(title=f'Command stats for #{channel.name}')
        embed.description = f'> **{channel.mention}** has `{sum(sorted_commands[d] for d in sorted_commands)}` command uses'

        embed.add_field(
            name='Most used commands:',
            value=better_string(
                [f'{list(sorted_commands.keys()).index(d)}. {d} (`{sorted_commands[d]}` times)' for d in sorted_commands],
                seperator='\n',
            ),
        )

        embed.set_author(name=channel.name, icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        name='commandstats',
        aliases=['stats'],
        help='Get command stats of a user, channel, server or overall.',
        with_app_command=False,
        hidden=True,
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def command_stats(
        self,
        ctx: Context,
        entity: discord.User | discord.Member | discord.abc.GuildChannel | discord.Guild | None = None,
    ) -> None:
        if not ctx.guild and not isinstance(entity, discord.Guild):
            entity = ctx.author

        if entity:
            if isinstance(entity, discord.User | discord.Member):
                return await self.handle_user(ctx, entity, ctx.guild)
            if isinstance(entity, discord.abc.GuildChannel):
                return await self.handle_channel(ctx, entity)

        await self.handle_user(ctx, ctx.author, ctx.guild)
        # We have handled user and channel and made sure we handle user when theres no guild

        return None
