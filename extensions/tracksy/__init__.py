from __future__ import annotations

from typing import TYPE_CHECKING

from extensions.tracksy.frontend import Frontend
from extensions.tracksy.tracker import Tracker

if TYPE_CHECKING:
    from utilities.bases.bot import Cyrene


class Tracksy(Tracker, Frontend, name='Tracksy'): ...


async def setup(bot: Cyrene) -> None:
    await bot.add_cog(Tracksy(bot))
