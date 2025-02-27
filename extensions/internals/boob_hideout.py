from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from utils import BaseCog

if TYPE_CHECKING:
    from utils import Context


def is_boob_hideout(ctx: Context) -> bool:
    return bool(ctx.guild and ctx.guild.id == 774561547930304536)


class BoobHideout(BaseCog):
    @commands.command('bhvc', help='Get members who are in vc in boob hideout')
    @commands.check(is_boob_hideout)
    async def wvc(self, ctx: Context) -> None:
        guild = self.bot.get_guild(774561547930304536)
        if not guild:
            return
        text = '\n'.join(
            [f'## {ch.name}\n{",".join([str(mem) for mem in ch.members])}\n' for ch in guild.voice_channels if ch.members],
        )
        await ctx.reply(text)
