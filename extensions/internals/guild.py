from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Literal

import discord
from discord.ext import commands

from utilities.bases.cog import MafuCog
from utilities.embed import Embed
from utilities.functions import fmt_str, timestamp_str

if TYPE_CHECKING:
    from collections.abc import Sequence


BOT_FARM_THRESHOLD = 75
BLACKLIST_COLOUR = discord.Colour.from_str('#ccaa88')
BOT_FARM_COLOUR = discord.Colour.from_str('#fff5e8')


def bot_farm_check(guild: discord.Guild) -> bool:
    bots = len([_ for _ in guild.members if _.bot is True])
    members = len(guild.members)
    return (bots / members) * 100 > BOT_FARM_THRESHOLD


def guild_embed(
    guild: discord.Guild, event_type: Literal['Joined', 'Left'], *, is_blacklisted: bool = False, is_bot_farm: bool = False
) -> Embed:
    embed = Embed(
        description=(
            f'- **Owner:** {guild.owner.mention if guild.owner else f"<@{guild.owner_id}>"} (`{guild.owner_id}`)\n'
            f'- **ID: ** {guild.id}\n'
            f'- **Created:** {timestamp_str(guild.created_at, with_time=True)}\n'
            f'- **Member Count:** `{guild.member_count}`\n'
        ),
    )
    embed.set_author(name=f'{event_type} {guild}', icon_url=guild.icon.url if guild.icon else None)

    embed_field_s: list[str] = []

    if is_bot_farm is True:
        embed.colour = BOT_FARM_COLOUR
        embed_field_s.append('- This guild is a bot farm.')
    if is_blacklisted is True:
        embed.colour = BLACKLIST_COLOUR
        embed_field_s.append('- This guild is blacklisted.')

    embed.add_field(value=fmt_str(embed_field_s, seperator='\n'))

    # I dont really care about the colour if they are both.

    return embed


def find_base_channel(channels: Sequence[discord.abc.GuildChannel]) -> discord.abc.GuildChannel | None:
    if (chs := [ch for ch in channels if 'general' in ch.name or 'chat' in ch.name]) and chs:
        return chs[0]
    return channels[0] if channels else None


class Guild(MafuCog):
    @commands.Cog.listener('on_guild_join')
    async def guild_join(self, guild: discord.Guild) -> None:
        is_blacklisted = self.bot.is_blacklisted(guild)
        is_bot_farm = bot_farm_check(guild)

        embed = guild_embed(
            guild,
            'Joined',
            is_blacklisted=bool(is_blacklisted),
            is_bot_farm=is_bot_farm,
        )

        await self.bot.logger.send(embed=embed)

        if not is_bot_farm:
            return

        ch = find_base_channel(guild.channels)
        if ch and isinstance(ch, discord.abc.Messageable):
            with contextlib.suppress(discord.HTTPException):
                await ch.send(f'{guild.name} is a bot farm. Therefore, I will be the server')
                await guild.leave()

    @commands.Cog.listener('on_guild_remove')
    async def guild_leave(self, guild: discord.Guild) -> None:
        is_blacklisted = self.bot.is_blacklisted(guild)
        is_bot_farm = bot_farm_check(guild)

        embed = guild_embed(
            guild,
            'Left',
            is_blacklisted=bool(is_blacklisted),
            is_bot_farm=is_bot_farm,
        )

        await self.bot.logger.send(embed=embed)
