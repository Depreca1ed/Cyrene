from datetime import datetime
from typing import Literal, NamedTuple

__all__ = ('BlacklistBase', 'WaifuResult')


class BlacklistBase(NamedTuple):
    reason: str
    lasts_until: datetime | None
    blacklist_type: Literal['guild', 'user']


class WaifuResult(NamedTuple):
    name: str | None
    dominant_color: str | None
    image_id: str | int
    source: str | None
    url: str
