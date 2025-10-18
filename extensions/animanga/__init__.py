from __future__ import annotations

from typing import TYPE_CHECKING

from .waifu import Waifu

if TYPE_CHECKING:
    from utilities.bases.bot import Elysia


class AniManga(Waifu, name='Anime & Manga'):
    """For everything related to Anime or Manga."""


async def setup(bot: Elysia) -> None:
    await bot.add_cog(AniManga(bot))
