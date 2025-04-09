from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
import mystbin
from discord.ext import commands

if TYPE_CHECKING:
    from asyncpg import Pool, Record

    from utilities.bases.bot import Mafuyu  # noqa: F401


class MafuContext(commands.Context['Mafuyu']):
    @discord.utils.copy_doc(commands.Context['Mafuyu'].reply)
    async def reply(self, content: str | None = None, **kwargs: Any) -> discord.Message:
        try:
            return await super().reply(content=content, **kwargs)
        except discord.HTTPException:
            return await super().send(content=content, **kwargs)

    @discord.utils.copy_doc(commands.Context['Mafuyu'].send)
    async def send(
        self,
        content: None | str = None,
        **kwargs: Any,
    ) -> discord.Message:
        if content and (c := str(content)) and len(c) > 1990:  # 2000 sounds a bit extreme to edge, safe at 1990
            paste = await self.bot.create_paste(f'Requested by {self.author}', content=content)
            content = (
                'The response which was supposed to be here was too big. I have posted it to MystBin instead\n'
                f'-# Link: {paste.url}'
            )

        return await super().send(
            content=content,
            **kwargs,
        )

    @property
    def pool(self) -> Pool[Record]:
        """
        Return the asyncpg Pool used in the bot.

        This can be considered an alias to bot.pool

        Returns
        -------
        Pool[Record]
            The asynpg pool used in the bot.

        """
        return self.bot.pool

    async def create_paste(self, filename: str, content: str) -> mystbin.Paste:
        """
        Create a mystbin paste.

        This is an alias to bot.create_paste

        Parameters
        ----------
        filename : str
            The name of the file in paste
        content : str
            The contents of the file

        Returns
        -------
        mystbin.Paste
            The created paste

        """
        file = mystbin.File(filename=filename, content=content)
        return await self.bot.mystbin.create_paste(files=[file])
