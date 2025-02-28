from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Any, Literal

from jishaku.paginators import WrappedFilePaginator, PaginatorInterface

if TYPE_CHECKING:
    from utils import Context, Mafuyu

import contextlib

import discord
from discord.ext import commands

from utils import BLACKLIST_COLOUR, BOT_FARM_COLOUR, BOT_THRESHOLD, Embed, better_string

from .blacklist import Blacklist
from .boob_hideout import BoobHideout
from .dev import Developer
from .error_handler import ErrorHandler


def guild_embed(guild: discord.Guild, event_type: Literal['Joined', 'Left']) -> Embed:
    return Embed(
        description=better_string(
            [
                f'- **Owner:** {guild.owner.mention if guild.owner else f"<@{guild.owner_id}>"} (`{guild.owner_id}`)',
                f'- **ID: ** {guild.id}',
                f'- **Created:** {discord.utils.format_dt(guild.created_at, "D")} ({discord.utils.format_dt(guild.created_at, "R")})',  # noqa: E501
                f'- **Member Count:** `{guild.member_count}`',
            ],
            seperator='\n',
        ),
    ).set_author(name=f'{event_type} {guild}', icon_url=guild.icon.url if guild.icon else None)


def bot_farm_check(guild: discord.Guild) -> bool:
    bots = len([_ for _ in guild.members if _.bot is True])
    members = len(guild.members)
    return (bots / members) * 100 > BOT_THRESHOLD


class Internals(Blacklist, Developer, ErrorHandler, BoobHideout, name='Developer'):
    def __init__(self, bot: Mafuyu) -> None:
        super().__init__(bot)

    @discord.utils.copy_doc(commands.Cog.cog_check)
    async def cog_check(self, ctx: Context) -> bool:
        if await self.bot.is_owner(ctx.author):
            return True
        msg = 'You do not own this bot.'
        raise commands.NotOwner(msg)

    @commands.Cog.listener('on_message_edit')
    async def edit_mechanic(self, _: discord.Message, after: discord.Message) -> None:
        if await self.bot.is_owner(after.author):
            await self.bot.process_commands(after)

    @commands.Cog.listener('on_reaction_add')
    async def delete_message(self, reaction: discord.Reaction, user: discord.Member | discord.User) -> None:
        if (
            await self.bot.is_owner(user)
            and reaction.emoji
            and reaction.emoji == '🗑️'
            and reaction.message.author.id == self.bot.user.id
        ):
            with contextlib.suppress(discord.HTTPException):
                await reaction.message.delete()

    @commands.Cog.listener('on_dbl_vote')
    async def dbl_vote_handler(self, data: dict[Any, Any]) -> None:
        await self.bot.logger.send(content=str(data))

    @commands.Cog.listener('on_guild_join')
    async def guild_join(self, guild: discord.Guild) -> None:
        blacklisted = bot_farm = False
        cog = self.bot.get_cog('internals')
        if cog and self.bot.is_blacklisted(guild):
            blacklisted = True
        if bot_farm_check(guild):
            bot_farm = True

        embed = guild_embed(guild, 'Joined')
        embed.colour = (
            (BLACKLIST_COLOUR if blacklisted is True else None) or (BOT_FARM_COLOUR if bot_farm is True else None) or None
        )

        if blacklisted or bot_farm:
            embed.add_field(
                value=better_string(
                    (
                        (
                            '- This guild is blacklisted. I have left the server automatically'
                            if blacklisted is True
                            else None
                        ),
                        '- This guild is a bot farm' if bot_farm is True else None,
                    ),
                    seperator='\n',
                )
            )

        await self.bot.logger.send(embed=embed)

    @commands.Cog.listener('on_guild_remove')
    async def guild_leave(self, guild: discord.Guild) -> None:
        embed = guild_embed(guild, 'Left')
        await self.bot.logger.send(embed=embed)

    @commands.command(name='file-to-pages', help='Turns a file into a pages to browse through', aliases=['ftp'])
    async def ftp(self, ctx: Context, attachment: discord.Attachment | None) -> discord.Message | PaginatorInterface:
        if not attachment and ctx.message.reference and isinstance(ctx.message.reference.resolved, discord.Message):
            attachment = ctx.message.reference.resolved.attachments[0]

        if not attachment:
            raise commands.MissingRequiredArgument(commands.parameter(displayed_name='attachment'))

        if attachment.size > 1024 * 1024 * 10:
            return await ctx.send('File larged than 10MB')

        if attachment.content_type and not attachment.content_type.startswith('text'):
            return await ctx.send('Not a text document')

        paginator = WrappedFilePaginator(BytesIO(await attachment.read()), max_size=1980)
        interface = PaginatorInterface(self.bot, paginator)
        return await interface.send_to(ctx)


async def setup(bot: Mafuyu) -> None:
    await bot.add_cog(Internals(bot))
