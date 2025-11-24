from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Literal, NamedTuple

from discord import TextChannel

if TYPE_CHECKING:
    import discord
    from discord.types.channel import Channel


class PullType(enum.IntEnum):
    PULLALL = 1
    SINGLE_PULL = 2
    PACK = 3
    WEEKLY_PULL = 4


class PackPullView(enum.IntEnum):
    PAGED_VIEW = 1
    LIST_VIEW = 2


class PartialCard(NamedTuple):
    id: int
    name: str
    rarity: int | Literal['EVENT']


class Card(NamedTuple):
    channel: TextChannel
    message: int
    user: discord.User | discord.Member
    id: int
    name: str
    rarity: int
    source: PullType


class Pull(NamedTuple):
    type: PullType
    user: discord.User | discord.Member
    cards: list[PartialCard]
