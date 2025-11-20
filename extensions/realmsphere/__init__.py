from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from utilities.bases.cog import CyCog

if TYPE_CHECKING:
    from utilities.bases.bot import Cyrene


class RealmSphere(CyCog, name='Realm Sphere'):
    async def cog_load(self) -> None:
        with Path('extensions/realmsphere/schema.sql').open(encoding='utf-8') as file:  # noqa: ASYNC230
            await self.bot.pool.execute(file.read())


async def setup(bot: Cyrene) -> None:
    await bot.add_cog(RealmSphere(bot))
