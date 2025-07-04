from __future__ import annotations

import asyncio
import datetime
import enum
from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Any, Self

import asyncpg
import discord

if TYPE_CHECKING:
    from utilities.bases.bot import Mafuyu


__all__ = (
    'ReservedTimerType',
    'Timer',
    'TimerManager',
)


class ReservedTimerType(enum.IntEnum):
    ANICORD_GACHA = 1


class Timer:
    def __init__(self, data: asyncpg.Record) -> None:
        self.id: int = data['id']
        self.user_id: int = data['user_id']
        self.reserved_type: int | None = data['reserved_type']
        self.expires: datetime.datetime = data['expires']

        super().__init__()

    @classmethod
    async def from_fetched_record(
        cls,
        pool: asyncpg.Pool[asyncpg.Record],
        *,
        id: int | None = None,
        user: discord.User | discord.Member | None = None,
        reserved_type: ReservedTimerType | None = None,
    ) -> Self | None:
        if id is None and user is None and reserved_type is None:
            raise TypeError('Expected at least one of the kwargs.')

        query = 'SELECT * FROM Timers WHERE '

        params: list[str] = []
        args: list[Any] = []

        if id:
            params.append(f'id = ${len(params) + 1}')
            args.append(id)

        if user:
            params.append(f'user_id = ${len(params) + 1}')
            args.append(user.id)

        if reserved_type:
            params.append(f'reserved_type = ${len(params) + 1}')
            args.append(reserved_type)

        query += ' AND '.join(params) + ' ORDER BY expires LIMIT 1'

        record = await pool.fetchrow(
            query,
            *args,
        )
        if not record:
            return None
        return cls(record)


class TimerManager:
    def __init__(self, loop: AbstractEventLoop, bot: Mafuyu) -> None:
        self.loop = loop
        self.bot = bot

        self.task = self.loop.create_task(self.dispatch_timers())
        self._have_data = asyncio.Event()

        self.current: Timer | None = None

        super().__init__()

    async def dispatch_timers(self) -> None:
        try:
            while not self.bot.is_closed():
                data = await self.wait_for_active_timer()

                self.current = Timer(data)

                now = datetime.datetime.now(tz=datetime.UTC)

                if self.current.expires >= now:
                    to_sleep = (self.current.expires - now).total_seconds()

                    await asyncio.sleep(to_sleep)

                await self.call_timer(self.current)

        except asyncio.CancelledError:
            raise

        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self.restart_task()

    async def wait_for_active_timer(self) -> asyncpg.Record:
        data = await self.fetch_closest_timer()

        if data is not None:
            self._have_data.set()
            return data

        self._have_data.clear()
        self.current = None

        await self._have_data.wait()  # Holds until set

        return await self.fetch_closest_timer()  # pyright: ignore[reportReturnType]

    async def fetch_closest_timer(self) -> asyncpg.Record | None:
        query = """
                SELECT
                    *
                FROM
                    Timers
                WHERE
                    expires < (CURRENT_TIMESTAMP + $1::interval)
                ORDER BY
                    expires
                LIMIT
                    1;
                """
        return await self.bot.pool.fetchrow(query, datetime.timedelta(days=40))

    async def call_timer(self, timer: Timer) -> None:
        self.bot.dispatch('timer_expire', timer)

        await self.bot.pool.execute('DELETE FROM Timers WHERE id = $1', timer.id)

    async def create_timer(
        self,
        when: datetime.datetime,
        *,
        user: discord.User | discord.Member,
        reserved_type: int | None = None,
        data: dict[Any, Any] | None = None,
    ) -> Timer:
        record = await self.bot.pool.fetchrow(
            """
            INSERT INTO
                Timers (user_id, expires, reserved_type, data)
            VALUES
                ($1, $2, $3, $4)
            RETURNING
                *;
            """,
            user.id,
            when,
            reserved_type,
            data,
        )
        assert record is not None

        timer = Timer(record)

        now = datetime.datetime.now(tz=datetime.UTC)
        dur = when - now

        if dur.total_seconds() <= (86400 * 40):
            self._have_data.set()

        if self.current and when < self.current.expires:
            self.restart_task()

        return timer

    async def cancel_timer(
        self,
        *,
        id: int | None = None,
        user: discord.User | discord.Member | None = None,
        reserved_type: ReservedTimerType | None = None,
    ) -> None:
        if id is None and user is None and reserved_type is None:
            raise TypeError('Expected at least one of the kwargs.')

        query = 'DELETE FROM Timers WHERE '

        params: list[str] = []
        args: list[Any] = []

        if id:
            params.append(f'id = ${len(params) + 1}')
            args.append(id)

        if user:
            params.append(f'user_id = ${len(params) + 1}')
            args.append(user.id)

        if reserved_type:
            params.append(f'reserved_type = ${len(params) + 1}')
            args.append(reserved_type)

        query += ' AND '.join(params)

        await self.bot.pool.execute(
            query,
            *args,
        )
        self.restart_task()

    def restart_task(self) -> None:
        self.task.cancel()
        self.task = self.loop.create_task(self.dispatch_timers())

    def close(self) -> None:
        self.task.cancel()
