from __future__ import annotations

from typing import TYPE_CHECKING

from discord import VoiceChannel
from discord.ext import commands

from utils import BaseCog, better_string

if TYPE_CHECKING:
    from utils import Context


def is_boob_hideout(ctx: Context):
    return bool(ctx.guild and ctx.guild.id == 774561547930304536)


class BoobHideout(BaseCog):
    @commands.command('wvc', help='Get members of the W vc channel')
    @commands.check(is_boob_hideout)
    async def wvc(self, ctx: Context) -> None:
        vc = self.bot.get_channel(1159930871718101072)
        if not isinstance(vc, VoiceChannel):
            return
        await ctx.reply(
            better_string(
                [
                    f'## {vc.name}',
                    f'- **Members:** {",".join([str(a) for a in vc.members])}',
                ],
                seperator='\n',
            )
        )
