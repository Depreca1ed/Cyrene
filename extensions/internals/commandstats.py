from __future__ import annotations

from discord import app_commands
from discord.ext import commands

from utils import BaseCog, Context


class CommandStats(BaseCog):
    @commands.hybrid_command(
        name='commandstats',
        aliases=['stats'],
        help='Get command stats of a user, channel, server or overall.',
        with_app_command=False,
        hidden=True,
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def command_stats(self, ctx: Context) -> None:
        pass
