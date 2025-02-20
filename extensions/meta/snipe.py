from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, Embed

if TYPE_CHECKING:
    from utils import Context


class Snipe(BaseCog):
    snipe_data: dict[int, discord.Message]
    snipe_optouts: list[int]

    async def cog_load(self) -> None:
        self.snipe_data = {}

        data = await self.bot.pool.fetch(
            """SELECT * FROM Feature WHERE allowed = $1 AND feature_type = $2""",
            False,
            'snipe',
        )
        self.snipe_optouts = [int(s['user_id'] or s['guild_id']) for s in data]

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if (message.guild and message.guild.id in self.snipe_optouts) or message.author.id in self.snipe_optouts:
            return
        self.snipe_data[message.channel.id] = message
        await asyncio.sleep(120)
        if message.channel.id in self.snipe_data:
            del self.snipe_data[message.channel.id]

    @commands.hybrid_command(
        name='snipe',
        description='Get information about the most recently deleted message in a channel',
        with_app_command=False,
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.guild_only()
    async def snipecmd(self, ctx: Context) -> discord.Message | None:
        if ctx.author.id in self.snipe_optouts or (ctx.guild and ctx.guild.id in self.snipe_optouts):
            return await ctx.reply('Optout msg placeholder')

        if ctx.channel.id not in self.snipe_data:
            return await ctx.send('No recently deleted messages found in the last 2 minutes for this channel.')

        message_data = self.snipe_data[ctx.channel.id]

        base_embed = Embed(
            ctx=ctx,
            description=message_data.content or '-# No base message content',
            color=message_data.author.color or message_data.author.accent_color or None,
        )
        base_embed.set_author(
            name=f'Sent by {message_data.author!s} in #{message_data.channel!s}',
            icon_url=message_data.author.display_avatar.url,
        )
        base_embed.set_image(url=message_data.attachments[0].url if message_data.attachments else None)
        base_embed.timestamp = message_data.created_at

        if message_data.reference:
            base_embed.add_field(
                name=str(
                    'Replying to '
                    + (
                        str(message_data.reference.resolved.author)
                        if message_data.reference.resolved
                        and not isinstance(message_data.reference.resolved, discord.DeletedReferencedMessage)
                        else 'Deleted message'
                    )
                ),
                value=message_data.reference.jump_url,
                inline=False,
            )
        embeds = [base_embed]

        embeds.extend(list(message_data.embeds))  # pyright: ignore[reportArgumentType]
        return await ctx.send(embeds=embeds)
