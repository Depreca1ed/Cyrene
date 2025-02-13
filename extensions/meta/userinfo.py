from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, Embed, better_string, generate_timestamp_string

if TYPE_CHECKING:
    from utils import Context


class Userinfo(BaseCog):
    def _get_acknowledgements(self, user: discord.Member) -> list[str]:
        acknowledgements: list[str] = []
        if [
            perm
            for perm in user.guild_permissions
            if perm in [subperm for subperm in discord.Permissions.elevated() if subperm[1] is True] and perm[1] is True
        ]:
            acknowledgements.append('- **Server Staff**')
        if user.id == user.guild.owner_id:
            acknowledgements.append('- **Server Owner**')
        return acknowledgements

    @commands.hybrid_command(name='whois', help='Get information about a user', aliases=['userinfo', 'who'])
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
            ctx=ctx,
        )

        name = f'{user.global_name or user.name} ' + (
            f'({user.nick} in {user.guild.name})'
            if isinstance(user, discord.Member) and user.nick and user.guild.name
            else ''
        )

        embed.set_author(
            name=name,
            icon_url=user.avatar.url if user.avatar else user.default_avatar.url,
        )

        basic_user_listing: list[str | None] = [
            f'- **ID:** `{user.id}`',
            f'- **Created:** {generate_timestamp_string(user.created_at)}',
        ]

        base_shown_count = 5
        acknoledgements: list[str] | None = None

        if isinstance(user, discord.Member):
            valid_roles = [role.mention for role in user.roles if role is not user.guild.default_role]
            valid_roles.reverse()

            roles_string = (
                ', '.join(valid_roles)
                if len(valid_roles) <= base_shown_count
                else ', '.join(valid_roles[:base_shown_count]) + f' + {len(valid_roles) - base_shown_count} roles'
            )

            member_listing = [
                (f'- **Joined:** {generate_timestamp_string(user.joined_at)}' if user.joined_at else None),
                f'- **Roles: ** {roles_string}' if valid_roles else None,
            ]

            if member_listing:
                basic_user_listing.extend(member_listing)

            if not user.guild_avatar:
                embed.set_author(name=embed.author.name, icon_url=None)

            acknoledgements = self._get_acknowledgements(user)

        embed.description = better_string(
            basic_user_listing,
            seperator='\n',
        )

        if acknoledgements:
            embed.add_field(name='Acknowledgements', value='\n'.join(acknoledgements), inline=False)

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=user.banner.url if user.banner else None)

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name='avatar',
        help="Get your or user's displayed avatar. By default, returns your server avatar",
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

        embed = Embed(title=f"{user}'s avatar", colour=user.color, ctx=ctx).set_image(url=avatar.url)

        filetypes = set(discord.asset.VALID_ASSET_FORMATS if avatar.is_animated() else discord.asset.VALID_STATIC_FORMATS)
        urls_string = better_string(
            [f'[{filetype.upper()}]({avatar.with_format(filetype)})' for filetype in filetypes],  # pyright: ignore[reportArgumentType]
            seperator=' **|** ',
        )
        embed.description = urls_string

        return await ctx.send(embed=embed)

    @commands.hybrid_command(name='icon', help="Get the server's icon, if any")
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

        embed = Embed(title=f"{ctx.guild}'s icon", ctx=ctx).set_image(url=icon.url)

        filetypes = set(discord.asset.VALID_ASSET_FORMATS if icon.is_animated() else discord.asset.VALID_STATIC_FORMATS)

        urls_string = better_string(
            [f'[{filetype.upper()}]({icon.with_format(filetype)})' for filetype in filetypes],  # pyright: ignore[reportArgumentType]
            seperator=' **|** ',
        )
        embed.description = urls_string

        return await ctx.send(embed=embed)
