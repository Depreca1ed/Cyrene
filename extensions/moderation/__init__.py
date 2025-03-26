from __future__ import annotations

from typing import TYPE_CHECKING

from .actions import Actions

if TYPE_CHECKING:
    from utils import Mafuyu


class Moderation(Actions): ...


async def setup(bot: Mafuyu):
    await bot.add_cog(Moderation(bot))
