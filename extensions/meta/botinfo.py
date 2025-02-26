from __future__ import annotations

import datetime
import pathlib
import platform

import discord
import git
import psutil
from discord import app_commands
from discord.ext import commands
from jishaku.math import natural_size

from utils import BaseCog, Context, Embed, better_string


class BotInformation(BaseCog):
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

    @commands.hybrid_command(name='about', aliases=['info', 'botinfo'], help='Get information about this bot', usage='')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def botinfo(
        self,
        ctx: Context,
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
            ctx=ctx,
        )

        owner = bot.appinfo.team.owner if bot.appinfo.team and bot.appinfo.team.owner else bot.owner

        embed.set_author(
            name=f'Made by {owner}',
            icon_url=owner.display_avatar.url,
        )
        embed.add_field(
            value=better_string(
                [
                    (
                        f'> I am in **{len(bot.guilds)} servers** '
                        f'and can see **{len(bot.users)} users** (`{len([_ for _ in bot.users if _.bot is True])} bots`)'
                    ),
                    (
                        f'> - **Installed by :** {self.bot.appinfo.approximate_user_install_count} users'
                        if self.bot.appinfo.approximate_user_install_count
                        else None
                    ),
                    (
                        f'- **Channels :** {channels["total"]}\n'
                        f'  - -# {channels["text"]} Text & {channels["voice"]} Voice channels'
                    )
                    if channels['total'] > 0
                    else None,
                ],
                seperator='\n',
            ),
        )

        proc = psutil.Process()
        with proc.oneshot():
            memory = proc.memory_info().rss
            memory_usage = natural_size(memory)

        uptime = discord.utils.format_dt(bot.start_time, 'R')
        is_loaded = len([_ for _ in bot.initial_extensions if _ in bot.extensions])
        usable_commands = 0
        for cog in bot.cogs:
            cog_resolved = bot.get_cog(cog)
            if not cog_resolved or cog.lower() == 'jishaku':
                continue
            for cmd in cog_resolved.walk_commands():
                valid = True
                for check in cmd.checks:
                    try:
                        cmd_check = await discord.utils.maybe_coroutine(check, ctx)
                    except commands.CheckFailure:
                        cmd_check = False
                    if cmd_check:
                        continue
                    valid = False
                    break
                if valid:
                    usable_commands += 1

        embed.add_field(
            name='Internal Statistics',
            value=better_string(
                [
                    f'- **Uptime :** {uptime}',
                    f'- **Memory :** `{memory_usage}` (`{round(proc.memory_percent(), 2)}%`)',
                    f'- **Categories :** {is_loaded}/{len(bot.initial_extensions)} enabled',
                    f'  - **Commands :** {usable_commands} usable commands',
                ],
                seperator='\n',
            ),
        )

        embed.add_field(
            value=better_string(
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
        embed.set_image(url=(bot.user.banner or (await bot.fetch_user(bot.user.id)).banner))
        embed.set_footer(text=f'Made in Python{platform.python_version()} using discord.py{discord.__version__}')

        await ctx.send(embed=embed)

    @commands.hybrid_command(name='support', help='Get invite link to the support server for the bot')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def support(self, ctx: Context) -> None:
        await ctx.reply(str(self.bot.support_invite))

    @commands.hybrid_command(name='invite', help='Get the URL for inviting me to a server or adding it to your account')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def invite(self, ctx: Context) -> None:
        await ctx.reply(str(self.bot.invite_url))

    @commands.hybrid_command(name='vote', help='Get the top.gg vote link for the bot')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def vote(self, ctx: Context) -> None:
        await ctx.reply(str(self.bot.topgg_url))
