from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

import discord

from utils.constants import BotEmojis

from . import BASE_COLOUR, CHAR_LIMIT, ERROR_COLOUR
from .helper_functions import better_string

if TYPE_CHECKING:
    import asyncpg

    from . import Context, Mafuyu

__all__ = ('Embed',)


class Embed(discord.Embed):
    def __init__(
        self,
        *,
        title: str | None = None,
        url: str | None = None,
        description: str | None = None,
        colour: discord.Colour | int | None = BASE_COLOUR,
        ctx: Context | None = None,
        **kwargs: Any,
    ) -> None:
        if ctx:
            self.set_footer(
                text=f'Requested by {ctx.author}',
            )
        super().__init__(
            title=title,
            url=url,
            description=description,
            colour=(colour if colour and colour != discord.Colour.default() else BASE_COLOUR),
            timestamp=discord.utils.utcnow(),
            **kwargs,
        )

    def add_field(self, *, name: str | None = '', value: str | None = '', inline: bool = False) -> Self:
        return super().add_field(name=name, value=value, inline=inline)

    @classmethod
    def error_embed(
        cls,
        *,
        title: str | None = None,
        description: str | None = None,
        ctx: Context | None = None,
    ) -> Self:
        """
        Generate an embed for error handler responses.

        Parameters
        ----------
        title : str | None, optional
            The title for the embed
        description : str | None, optional
            The description for the embed
        ctx : Context | None, optional
            The context for the embed, if applicable

        Returns
        -------
        Embed
            The generated embed

        """
        title = f'{BotEmojis.RED_CROSS} | {title}' if ctx else title
        return cls(title=title, description=description, ctx=ctx, colour=ERROR_COLOUR)

    @classmethod
    async def logger_embed(cls, bot: Mafuyu, record: asyncpg.Record) -> Self:
        """
        Generate an embed logged to the error logger.

        This embed is also used in the pagination for errors

        Parameters
        ----------
        bot : Mafuyu
            The bot this embed belongs to
        record : asyncpg.Record
            The record of the error

        Returns
        -------
        Embed
            The generated embed

        """
        error_link = await bot.create_paste(
            filename=f'error{record["id"]}.py',
            content=record['full_error'],
        )

        logger_embed = cls(
            title=f'Error #{record["id"]}',
            description=(
                f"""```py\n{record['full_error']}```"""
                if len(record['full_error']) < CHAR_LIMIT
                else 'Error message was too long to be shown'
            ),
            colour=0xFF0000 if record['fixed'] is False else 0x00FF00,
            url=error_link.url,
        )

        logger_embed.add_field(
            value=better_string(
                (
                    f'- **Command:** `{record["command"]}`',
                    f'- **User:** {bot.get_user(record["user_id"])}',
                    f'- **Guild:** {bot.get_guild(record["guild"]) if record["guild"] else "N/A"}',
                    f'- **URL: ** [Jump to message]({record["message_url"]})',
                    f'- **Occured: ** {discord.utils.format_dt(record["occured_when"], "f")}',
                ),
                seperator='\n',
            )
        )
        return logger_embed
