from __future__ import annotations

from typing import TYPE_CHECKING

from .anicord_gacha import AniCordGacha

if TYPE_CHECKING:
    from utils.subclass import Mafuyu


async def setup(bot: Mafuyu) -> None:
    await bot.add_cog(AniCordGacha(bot))
