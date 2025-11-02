from __future__ import annotations

from typing import TYPE_CHECKING

from extensions.tracksy.tracker import Tracker

if TYPE_CHECKING:
    from utilities.bases.bot import Cyrene


class Tracksy(Tracker, name='Tracksy'): ...


async def setup(bot: Cyrene) -> None:
    await bot.add_cog(Tracksy(bot))
