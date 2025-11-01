from __future__ import annotations

import enum
from typing import Literal, NamedTuple


class PullType(enum.IntEnum):
    PULLALL = 1
    SINGLE_PULL = 2
    PACK = 3
    WEEKLY_PULL = 4


class Card(NamedTuple):
    id: int
    name: str
    rarity: int | Literal['EVENT']
