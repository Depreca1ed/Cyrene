from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utilities.bases.cog import MafuCog
from utilities.embed import Embed
from utilities.functions import fmt_str, timestamp_str
from utilities.view import PermissionView

if TYPE_CHECKING:
    from utilities.bases.context import MafuContext


USER_DATA_OBJECT_COUNT = 5


class Userinfo(MafuCog):
    @commands.hybrid_command(name='whois', description='Get information about a user', aliases=['userinfo', 'who'])
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def whois(
        self,
        ctx: MafuContext,
        user: discord.Member | discord.User = commands.Author,
    ) -> None:
        embed = Embed(
            title=str(user),
            colour=user.colour if user.colour != discord.Colour.default() else None,
        )

        name = f'{user.global_name or user.name} '

        user_info: list[str | None] = [
            f'-# **Mutual Servers:** {len(user.mutual_guilds)}' if user.mutual_guilds else None,
            f'- **ID:** `{user.id}`',
            f'- **Created:** {timestamp_str(user.created_at, with_time=True)}',
        ]

        view = None

        if isinstance(user, discord.Member):
            is_guild_ok = bool(user.guild and user.guild.roles)  # When the guild is there, the guild will have @everyone

            if is_guild_ok:
                if user.nick:
                    name += f'({user.nick} in {user.guild.name})'
                view = PermissionView(ctx, target=user, permissions=user.guild_permissions)

            valid_roles = [role.mention for role in user.roles if role is not user.guild.default_role]
            valid_roles.reverse()

            roles_string = ', '.join(valid_roles[:USER_DATA_OBJECT_COUNT]) + (
                f' + {len(valid_roles) - USER_DATA_OBJECT_COUNT} roles' if len(valid_roles) > USER_DATA_OBJECT_COUNT else ''
            )

            member_info = [
                (f'- **Joined:** {timestamp_str(user.joined_at, with_time=True)}' if user.joined_at else None),
                f'- **Roles: ** {roles_string}' if valid_roles else None,
            ]

            if member_info:
                user_info.extend(member_info)

        embed.description = fmt_str(
            user_info,
            seperator='\n',
        )

        embed.set_author(
            name=name,
            icon_url=user.guild_avatar.url if isinstance(user, discord.Member) and user.guild_avatar else None,
        )

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=user.banner.url if user.banner else None)

        msg = await ctx.reply(embed=embed, view=view)
        if view:
            view.message = msg
