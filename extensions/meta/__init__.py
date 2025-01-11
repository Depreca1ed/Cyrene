from __future__ import annotations

from typing import TYPE_CHECKING

from .botinfo import BotInformation
from .serverinfo import ServerInfo
from .userinfo import Userinfo

if TYPE_CHECKING:
    from bot import Mafuyu


class Meta(BotInformation, Userinfo, ServerInfo, name='Meta'):
    """For everything related to Discord or Mafuyu."""


async def setup(bot: Mafuyu) -> None:
    await bot.add_cog(Meta(bot))
