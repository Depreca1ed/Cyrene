from __future__ import annotations

from typing import TYPE_CHECKING

from .waifu import Waifu

if TYPE_CHECKING:
    from utils import Mafuyu


class AniManga(Waifu, name='Anime & Manga'):
    """For everything related to Anime or Manga."""


async def setup(bot: Mafuyu) -> None:
    await bot.add_cog(AniManga(bot))
