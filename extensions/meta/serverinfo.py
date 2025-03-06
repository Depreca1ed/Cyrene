from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, Embed, better_string, generate_timestamp_string

if TYPE_CHECKING:
    from utils import Context


class ServerInfo(BaseCog):
    @commands.hybrid_command(name='serverinfo', help='Get information about the server')
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @commands.guild_only()
    async def serverinfo(self, ctx: Context) -> None:
        if not ctx.guild:
            msg = 'Guild not found'
            raise commands.GuildNotFound(msg)
        guild = ctx.guild

        embed = Embed(title=guild.name, description=guild.description or None)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        embed.add_field(
            value=better_string(
                [
                    f'- **Owner:** {guild.owner.mention if guild.owner else f"<@{guild.owner_id}>"} (`{guild.owner_id}`)',
                    f'- **ID: ** `{guild.id}`',
                    f'- **Created:** {generate_timestamp_string(guild.created_at)}',
                ],
                seperator='\n',
            ),
        )

        valid_roles = [role.mention for role in guild.roles if role is not guild.default_role]
        valid_roles.reverse()
        emojis = [str(emoji) for emoji in guild.emojis]
        base_show_count = 3
        embed.add_field(
            value=better_string(
                [
                    f'- **Members:** `{guild.member_count}`',
                    f'- **Channels:** `{len(guild.channels)}`',
                    (
                        better_string(
                            [
                                f'- **Roles: ** {", ".join(valid_roles) if len(valid_roles) <= base_show_count else ", ".join(valid_roles[:3]) + f" + {len(valid_roles) - base_show_count} roles"}'  # noqa: E501
                                if guild.roles
                                else None,
                                f'- **Emojis: ** {" ".join(emojis) if len(emojis) <= base_show_count else " ".join(emojis[:3]) + f" + {len(emojis) - 3} emojis"} (`{len(guild.emojis)}/{guild.emoji_limit}`)'  # noqa: E501
                                if guild.emojis
                                else None,
                            ],
                            seperator='\n',
                        )
                        if valid_roles
                        else None
                    ),
                ],
                seperator='\n',
            ),
        )

        if guild.premium_subscription_count:
            boosters = [
                str(a.mention)
                for a in sorted(
                    guild.premium_subscribers,
                    key=lambda m: (m.premium_since or (m.joined_at or m.created_at)),
                )
            ]

            embed.add_field(
                name='Nitro Boosts',
                value=better_string(
                    [
                        f'> **{guild.name}** has `{guild.premium_subscription_count}` boosts and is at **Level `{guild.premium_tier}`**',  # noqa: E501
                        (
                            f'- **Booster Role: ** {guild.premium_subscriber_role.mention}'
                            if guild.premium_subscriber_role
                            else None
                        ),
                        (
                            f'- **Boosters: ** {", ".join(boosters) if len(boosters) <= base_show_count else ", ".join(boosters[:3]) + f" + {len(boosters) - base_show_count} boosters"}'  # noqa: E501
                            if valid_roles
                            else None
                        ),
                    ],
                    seperator='\n',
                ),
            )

        banner_or_splash = guild.banner or guild.splash
        embed.set_image(url=banner_or_splash.url if banner_or_splash else None)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name='roleinfo', help='Get information about a role', aliases=['role'])
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=True)
    @commands.guild_only()
    async def roleinfo(self, ctx: Context, role: discord.Role) -> discord.Message:
        embed = Embed(
            title=f'{role.name} {role.unicode_emoji or ""}',
            colour=role.colour,
        )
        embed.description = better_string(
            (
                f'- **ID:** {role.id}',
                f'- **Created:** {discord.utils.format_dt(role.created_at, "D")} ({discord.utils.format_dt(role.created_at, "R")})',  # noqa: E501
                (f'> `{len(role.members)}` users have this role.' if role.members else None),
            ),
            seperator='\n',
        )
        embed.set_thumbnail(url=role.icon.url if role.icon else None)
        if role.is_premium_subscriber() or role.is_integration() or role.is_bot_managed():
            embed.add_field(
                value=better_string(
                    (
                        ('- This is a **server booster** role' if role.is_premium_subscriber() else None),
                        ('- This role is managed by an **integration**' if role.is_integration() else None),
                        ('- This role is for an **app**' if role.is_bot_managed() else None),
                    ),
                    seperator='\n',
                ),
            )
        return await ctx.reply(embed=embed)
