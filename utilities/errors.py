from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from datetime import datetime


__all__ = (
    'AlreadyBlacklistedError',
    'CyreneError',
    'FeatureDisabledError',
    'NotBlacklistedError',
    'PrefixAlreadyPresentError',
    'PrefixNotInitialisedError',
    'PrefixNotPresentError',
    'UnderMaintenanceError',
)


class CyreneError(discord.ClientException): ...


class FeatureDisabledError(commands.CheckFailure, CyreneError):
    def __init__(self) -> None:
        super().__init__('This feature is not enabled in this server.')


class PrefixNotInitialisedError(CyreneError):
    def __init__(self, guild: discord.Guild) -> None:
        super().__init__(f'Prefixes were not initialised for {guild.id}')


class PrefixAlreadyPresentError(commands.CommandError, CyreneError):
    def __init__(self, prefix: str) -> None:
        super().__init__(f"'{prefix} is an already present prefix.'")


class PrefixNotPresentError(commands.CommandError, CyreneError):
    def __init__(self, prefix: str, guild: discord.Guild) -> None:
        super().__init__(f'{prefix} is not present in guild: {guild.id}')


class AlreadyBlacklistedError(CyreneError):
    def __init__(
        self,
        snowflake: discord.User | discord.Member | discord.Guild,
        *,
        reason: str,
        until: datetime | None,
    ) -> None:
        self.snowflake = snowflake
        self.reason = reason
        self.until = until
        timestamp_wording = f'until {until}' if until else 'permanently'
        string = f'{snowflake} is already blacklisted for {reason} {timestamp_wording}'
        super().__init__(string)


class NotBlacklistedError(CyreneError):
    def __init__(self, snowflake: discord.User | discord.Member | discord.Guild | int) -> None:
        self.snowflake = snowflake
        super().__init__(f'{snowflake} is not blacklisted.')


class UnderMaintenanceError(commands.CheckFailure, CyreneError):
    def __init__(self) -> None:
        super().__init__('The bot is currently under maintenance.')


class WaifuNotFoundError(commands.CommandError, CyreneError):
    def __init__(self, waifu: str | None = None, json: dict[Any, Any] | str | None = None) -> None:
        waifu = waifu.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere') if waifu else None
        self.waifu = waifu
        self.json = json
        if waifu:
            super().__init__(f'Could not find any results for {waifu}\n{json}')
        else:
            super().__init__(message=f'Could not find any results\n{json}')


# TODO(Depreca1ed): All of these are not supposed to be CommandError. Change them to actual errors
