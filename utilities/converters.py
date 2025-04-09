from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import parsedatetime  # pyright: ignore[reportMissingTypeStubs]
from discord.ext import commands

if TYPE_CHECKING:
    from utilities.bases.context import MafuContext


class TimeConverter(commands.Converter[datetime.datetime]):
    async def convert(self, _: MafuContext, argument: str) -> datetime.datetime:
        dt_obj: tuple[datetime.datetime, int] = parsedatetime.Calendar().parseDT(argument)  # pyright: ignore[reportAssignmentType, reportUnknownMemberType]

        if dt_obj[1] == 0:
            msg = 'Invalid time provided'
            raise commands.BadArgument(msg)

        if dt_obj[0] < datetime.datetime.now():
            msg = "The time you've provided is in the past"
            raise commands.BadArgument(msg)

        return dt_obj[0]
