from __future__ import annotations

from typing import TYPE_CHECKING

from utils import BaseCog

if TYPE_CHECKING:
    from utils import Context


def is_boob_hideout(ctx: Context) -> bool:
    return bool(ctx.guild and ctx.guild.id == 774561547930304536)


class BoobHideout(BaseCog): ...
