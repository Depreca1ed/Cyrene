from __future__ import annotations

from typing import TYPE_CHECKING

from extensions.misc.ADGsuggestions import ADGSuggestions

from .AnicordGacha import AniCordGacha

if TYPE_CHECKING:
    from utilities.bases.bot import Mafuyu


async def setup(bot: Mafuyu) -> None:
    await bot.add_cog(AniCordGacha(bot))
    await bot.add_cog(ADGSuggestions(bot))
