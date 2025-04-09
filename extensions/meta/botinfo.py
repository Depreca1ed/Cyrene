from __future__ import annotations

import datetime
import pathlib
import platform
from typing import TYPE_CHECKING

import discord
import git
import psutil
from discord import app_commands
from discord.ext import commands
from jishaku.math import natural_size

from utilities.bases.cog import MafuCog
from utilities.embed import Embed
from utilities.functions import fmt_str, timestamp_str

if TYPE_CHECKING:
    from utilities.bases.context import MafuContext


class BotInformation(MafuCog):
    def get_commits(self, count: int = 5) -> list[git.Commit]:
        repo = git.Repo(pathlib.Path.cwd())
        return list(repo.iter_commits(repo.active_branch, max_count=count))

    def format_commit(self, commit: git.Commit) -> str:
        sha1 = commit.hexsha[:7]
        message = (
            commit.message.split('\n')[0] if isinstance(commit.message, str) else 'No message found.'
        )  # to stop ugly red line
        time = datetime.datetime.fromtimestamp(commit.committed_date, tz=datetime.UTC)

        time = round(time.timestamp())

        return f'**[[`{sha1}`](https://github.com/Depreca1ed/Mafuyu/commit/{commit.hexsha})]**: {message}'

    @commands.hybrid_command(
        name='about', aliases=['info', 'botinfo'], description='Get information about this bot', usage=''
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def botinfo(
        self,
        ctx: MafuContext,
    ) -> None:
        bot = self.bot

        channels = {'voice': 0, 'text': 0, 'total': 0}
        for channel in bot.get_all_channels():
            if channel.type in {discord.ChannelType.text, discord.ChannelType.news}:
                channels['text'] += 1
            elif channel.type in {discord.ChannelType.voice, discord.ChannelType.stage_voice}:
                channels['voice'] += 1
            channels['total'] += 1

        embed = Embed(
            title=str(bot.user.name),
            description='\n'.join([self.format_commit(c) for c in self.get_commits()]),
        )

        embed.set_author(
            name=f'Made by {bot.owner}',
            icon_url=bot.owner.display_avatar.url,
        )

        proc = psutil.Process()
        with proc.oneshot():
            memory = proc.memory_info().rss
            memory_usage = natural_size(memory)

        embed.add_field(
            name='Internal Statistics',
            value=fmt_str(
                [
                    f'- **Servers :** `{len(bot.guilds)}`',
                    f'- **Users :** `{len(bot.users)}` (`{len([_ for _ in bot.users if _.bot is True])} bots`)',
                    (
                        f'  - **Installed by :** {self.bot.appinfo.approximate_user_install_count} users'
                        if self.bot.appinfo.approximate_user_install_count
                        else None
                    ),
                    f'- **Uptime since:** {timestamp_str(bot.start_time, with_time=True)}',
                    f'- **Memory :** `{memory_usage}` (`{round(proc.memory_percent(), 2)}%`)',
                ],
                seperator='\n',
            ),
        )

        embed.add_field(
            value=fmt_str(
                [
                    (
                        (
                            f'-# [Privacy Policy]({bot.appinfo.privacy_policy_url})\n'
                            f'-# [Terms of Service]({bot.appinfo.terms_of_service_url})'
                        )
                        if bot.appinfo.terms_of_service_url and bot.appinfo.privacy_policy_url
                        else None
                    ),
                    f'-# [Invite the bot]({bot.invite_url})',
                    f'-# [Support Server]({bot.support_invite})',
                ],
                seperator='\n',
            ),
        )

        embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
        embed.set_footer(text=f'Made in Python{platform.python_version()} using discord.py{discord.__version__}')

        await ctx.send(embed=embed)

    @commands.hybrid_command(name='support', description='Get invite link to the support server for the bot')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def support(self, ctx: MafuContext) -> None:
        await ctx.reply(str(self.bot.support_invite))

    @commands.hybrid_command(
        name='invite', description='Get the URL for inviting me to a server or adding it to your account'
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def invite(self, ctx: MafuContext) -> None:
        await ctx.reply(str(self.bot.invite_url))
