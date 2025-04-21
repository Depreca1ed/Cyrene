from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from extensions.misc.AnicordGacha.constants import PULL_LINE_REGEX, RARITY_EMOJIS
from utilities.timers import ReservedTimerType, Timer

if TYPE_CHECKING:
    from asyncpg import Pool, Record
    from discord import Member, Message, User


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
    ) -> None:
        query = """
            INSERT INTO
                GachaPulledCards (user_id, message_id, card_id, card_name, rarity)
            VALUES
                ($1, $2, $3, $4, $5);
            """
        args = (
            self.user.id,
            pull_message.id,
            card.id,
            card.name,
            card.rarity,
        )
        await pool.execute(query, *args)


@dataclass
class PulledCard:
    id: int
    name: str | None
    rarity: int
    message_id: int | None = None

    @classmethod
    def parse_from_str(cls, s: str, /) -> None | Self:
        parsed = re.finditer(PULL_LINE_REGEX, s)

        if not parsed:
            return None

        for _ in parsed:
            d = _.groupdict()

            c_id = int(d['id'])
            rarity = next(k for k, _ in RARITY_EMOJIS.items() if _.name == d['rarity'])
            name: str = d['name']

            return cls(c_id, name, rarity)

        return None
