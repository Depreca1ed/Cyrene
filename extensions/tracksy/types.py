from __future__ import annotations

import enum


class PullType(enum.IntEnum):
    PULLALL = 1
    SINGLE_PULL = 2
    PACK = 3
    WEEKLY_PULL = 4
