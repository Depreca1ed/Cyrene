from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, Embed, PermissionView, better_string, generate_timestamp_string

if TYPE_CHECKING:
    from utils import Context


USER_DATA_OBJECT_COUNT = 5


class Userinfo(BaseCog):
    @commands.hybrid_command(name='whois', description='Get information about a user', aliases=['userinfo', 'who'])
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def whois(
        self,
        ctx: Context,
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
            f'- **Created:** {generate_timestamp_string(user.created_at)}',
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
                (f'- **Joined:** {generate_timestamp_string(user.joined_at)}' if user.joined_at else None),
                f'- **Roles: ** {roles_string}' if valid_roles else None,
            ]

            if member_info:
                user_info.extend(member_info)

        embed.description = better_string(
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

    @commands.hybrid_command(
        name='avatar',
        description="Get your or user's displayed avatar. By default, returns your server avatar",
        aliases=['av'],
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def avatar(
        self,
        ctx: Context,
        user: discord.User | discord.Member = commands.Author,
        *,
        server_avatar: bool = True,
    ) -> discord.Message:
        avatar = user.display_avatar if server_avatar is True else user.avatar or user.default_avatar

        embed = Embed(title=f"{user}'s avatar", colour=user.color).set_image(url=avatar.url)

        filetypes = set(discord.asset.VALID_ASSET_FORMATS if avatar.is_animated() else discord.asset.VALID_STATIC_FORMATS)
        urls_string = better_string(
            [f'[{filetype.upper()}]({avatar.with_format(filetype)})' for filetype in filetypes],  # pyright: ignore[reportArgumentType]
            seperator=' **|** ',
        )
        embed.description = urls_string

        return await ctx.send(embed=embed)

    @commands.hybrid_command(name='icon', description="Get the server's icon, if any")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @commands.guild_only()
    async def guild_avatar(self, ctx: Context) -> discord.Message:
        if not ctx.guild:
            msg = 'Guild not found'
            raise commands.GuildNotFound(msg)

        icon = ctx.guild.icon
        if not icon:
            return await ctx.reply(content=f'{commands.clean_content().convert(ctx, str(ctx.guild))} does not have an icon.')

        embed = Embed(title=f"{ctx.guild}'s icon").set_image(url=icon.url)

        filetypes = set(discord.asset.VALID_ASSET_FORMATS if icon.is_animated() else discord.asset.VALID_STATIC_FORMATS)

        urls_string = better_string(
            [f'[{filetype.upper()}]({icon.with_format(filetype)})' for filetype in filetypes],  # pyright: ignore[reportArgumentType]
            seperator=' **|** ',
        )
        embed.description = urls_string

        return await ctx.send(embed=embed)
