from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Literal, NamedTuple

if TYPE_CHECKING:
    import discord


class PullType(enum.IntEnum):
    PULLALL = 1
    SINGLE_PULL = 2
    PACK = 3
    WEEKLY_PULL = 4

class PackPullView(enum.IntEnum):
    PAGED_VIEW = 1
    LIST_VIEW = 2

class Card(NamedTuple):
    id: int
    name: str
    rarity: int | Literal['EVENT']


class Pull(NamedTuple):
    type: PullType
    user: discord.User | discord.Member
    cards: list[Card]
