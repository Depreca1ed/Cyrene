from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, NamedTuple


class CardFlags(IntEnum):
    NORMAL = 0


class Aeon(NamedTuple):
    name: str
    path: str
    alt_name: str | None
    perk: Any


@dataclass
class Theme:
    name: str
    description: str | None
    disabled: bool


@dataclass
class Character:
    name: str
    theme: Theme
    aeon: Aeon | None = None


@dataclass
class Card(NamedTuple):
    id: int
    name: str
    rarity: int
    characters: list[Character]
    flag: CardFlags | None = CardFlags.NORMAL
