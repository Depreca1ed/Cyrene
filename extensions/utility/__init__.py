from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from jishaku.paginators import PaginatorInterface, WrappedFilePaginator

from utils import BaseCog

if TYPE_CHECKING:
    from utils import Context, Mafuyu


class Utility(BaseCog, name='Utility'):
    """Some useful utility commands."""

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
    await bot.add_cog(Utility(bot))
