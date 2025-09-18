from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from extensions.misc.AnicordGacha.constants import PULLALL_LINE_REGEX, RARITY_EMOJIS, SINGLE_PULL_REGEX
from utilities.timers import ReservedTimerType, Timer

if TYPE_CHECKING:
    import discord
    from asyncpg import Pool, Record
    from discord import Member, Message, User

    from utilities.embed import Embed


class PullSource(enum.Enum):
    PULLALL = 1
    PULL = 2
    PACK = 3


class GachaUser:
    def __init__(self, user: User | Member, *, timer: Timer | None, config_data: Record) -> None:
        self.user = user
        self.timer = timer
        self.config_data = config_data
        super().__init__()

    @classmethod
    async def from_fetched_record(
        cls,
        pool: Pool[Record],
        *,
        user: User | Member,
    ) -> Self:
        timer = await Timer.from_fetched_record(
            pool,
            user=user,
            reserved_type=ReservedTimerType.ANICORD_GACHA,
        )

        record = await pool.fetchrow(
            """
            INSERT INTO
                GachaData (user_id)
            VALUES
                ($1)
            ON CONFLICT (user_id) DO
            UPDATE
            SET
                user_id = GachaData.user_id
            RETURNING
                *
            """,
            user.id,
        )
        assert record is not None

        return cls(user, timer=timer, config_data=record)

    async def add_card(
        self,
        pool: Pool[Record],
        *,
        card: PulledCard,
        pull_message: Message,
        source: PullSource,
    ) -> None:
        query = """
            INSERT INTO
                GachaPulledCards (user_id, message_id, card_id, card_name, rarity, pull_source)
            VALUES
                ($1, $2, $3, $4, $5, $6);
            """
        args = (
            self.user.id,
            pull_message.id,
            card.id,
            card.name,
            card.rarity,
            source.value,
        )
        await pool.execute(query, *args)


@dataclass
class PulledCard:
    id: int
    name: str
    rarity: int
    message_id: int | None = None
    user: User | None = None
    source: PullSource | None = None

    @classmethod
    def parse_from_pullall_str(cls, s: str, /) -> None | Self:
        parsed = re.finditer(PULLALL_LINE_REGEX, s)

        if not parsed:
            return None

        for _ in parsed:
            d = _.groupdict()

            c_id = int(d['id'])
            rarity = next(k for k, _ in RARITY_EMOJIS.items() if _.name == d['rarity'])
            name: str = d['name']

            return cls(c_id, name, rarity)

        return None

    @classmethod
    def parse_from_single_pull(cls, e: Embed | discord.Embed, /) -> None | Self:
        name = e.title

        assert name is not None
        assert e.description is not None

        parsed = re.finditer(SINGLE_PULL_REGEX, e.description)

        if not parsed:
            return None

        for _ in parsed:
            data = _.groupdict()

            c_id = int(data['id'])
            rarity = next(k for k, _ in RARITY_EMOJIS.items() if _.name == data['rarity'])
            # NOTE: Burn worth is.... useless..

            return cls(c_id, name, rarity)
        return None
