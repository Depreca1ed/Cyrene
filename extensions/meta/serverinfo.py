from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, Embed, better_string

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

        embed = Embed(description=guild.description or None, ctx=ctx)
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)

        embed.add_field(
            value=better_string(
                [
                    f'- **Owner:** {guild.owner.mention if guild.owner else f"<@{guild.owner_id}>"} (`{guild.owner_id}`)',
                    f'- **ID: ** {guild.id}',
                    f'- **Created:** {discord.utils.format_dt(guild.created_at, "D")} ({discord.utils.format_dt(guild.created_at, "R")})',  # noqa: E501
                ],
                seperator='\n',
            ),
        )

        valid_roles = [role.mention for role in guild.roles if role is not guild.default_role]
        valid_roles.reverse()
        emojis = [str(emoji) for emoji in guild.emojis]
        base_show_count = 3
        embed.add_field(
            name='Statistics',
            value=better_string(
                [
                    f'- **Members:** `{guild.member_count}`',
                    f'- **Channels:** `{len(guild.channels)}`',
                    (
                        better_string(
                            [
                                f'- **Roles: ** {", ".join(valid_roles) if len(valid_roles) <= base_show_count else ", ".join(valid_roles[:3]) + f" + {len(valid_roles) - base_show_count} roles"}',  # noqa: E501
                                f'- **Emojis: ** {" ".join(emojis) if len(emojis) <= base_show_count else " ".join(emojis[:3]) + f" + {len(emojis) - 3} emojis"} (`{len(guild.emojis)}/{guild.emoji_limit}`)',  # noqa: E501
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
