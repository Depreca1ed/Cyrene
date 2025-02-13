from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime

__all__ = ('BlacklistData', 'WaifuResult')


@dataclass
class BlacklistData:
    reason: str
    lasts_until: datetime | None
    blacklist_type: Literal['guild', 'user']


@dataclass
class WaifuResult:
    name: str | None
    image_id: str | int
    source: str | None
    url: str
    characters: str
    copyright: str

    def parse_string_lists(self, lists: str) -> list[str]:
        objs = lists.split(' ')
        return [obj.replace('_', ' ').title() for obj in objs]
