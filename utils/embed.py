from __future__ import annotations

from typing import Any, Self

import discord

from . import BASE_COLOUR, ERROR_COLOUR, Context

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
                icon_url=ctx.author.display_avatar.url or None,
            )
        super().__init__(
            title=title,
            url=url,
            description=description,
            colour=colour if colour and colour != discord.Colour.default() else BASE_COLOUR,
            **kwargs,
        )

    def add_field(self, *, name: str | None = '', value: str | None = '', inline: bool = False) -> Self:
        return super().add_field(name=name, value=value, inline=inline)

    @classmethod
    def error_embed(cls, *, title: str | None = None, description: str | None = None, ctx: Context | None = None) -> Self:
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
        return cls(title=title, description=description, ctx=ctx, colour=ERROR_COLOUR)
