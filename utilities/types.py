from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    import discord

__all__ = ('WaifuFavouriteEntry', 'WaifuResult')


@dataclass
class WaifuResult:
    image_id: str | int
    url: str
    characters: str
    copyright: str
    name: str | None = None
    source: str | None = None

    def parse_string_lists(self, lists: str) -> list[str]:
        objs = lists.split(' ')
        return [obj.replace('_', ' ').title() for obj in objs]


@dataclass
class WaifuFavouriteEntry:
    id: int
    user_id: discord.User
    nsfw: bool
    tm: datetime
