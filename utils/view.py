from __future__ import annotations

import contextlib
import traceback
from typing import TYPE_CHECKING, Any

import discord

from utils import Embed, better_string

if TYPE_CHECKING:
    from discord.ui.item import Item

    from bot import Mafuyu

__all__ = ('BaseView',)

CHAR_LIMIT = 2000


class BaseView(discord.ui.View):
    message: discord.Message | None

    async def on_timeout(self) -> None:
        with contextlib.suppress(discord.errors.NotFound):
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=None)
        self.stop()

    async def on_error(
        self,
        interaction: discord.Interaction[Mafuyu],
        error: Exception,
        _: Item[Any],
    ) -> None:
        func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await func(content=str(error) + '\n-# Developers have been informed')
        exc = f'```py\n{"".join(traceback.format_exception(type(error), error, error.__traceback__))}```'
        exc_link = await interaction.client.create_paste(filename='error', content=exc) if len(exc) > CHAR_LIMIT else None

        embed = Embed(
            title=error.__class__.__name__,
            description=exc,
            url=str(exc_link),
            colour=0x000000,
        )
        embed.add_field(
            value=better_string(
                [
                    f'> - **User: **{interaction.user!s}',
                    f'> - **Server: **{interaction.guild.name if interaction.guild else "No guild"!s}',
                    f'> - **View: **{self.__class__.__name__}',
                ],
                seperator='\n',
            ),
        )
        return await interaction.client.logger_webhook.send(embed=embed)
