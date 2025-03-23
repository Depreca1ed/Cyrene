from __future__ import annotations

import datetime
import traceback
from typing import TYPE_CHECKING, Any

import discord
import parsedatetime  # pyright: ignore[reportMissingTypeStubs]
from discord.ext import commands

if TYPE_CHECKING:
    from collections.abc import Iterable

    from . import Context


__all__ = (
    'TimeConverter',
    'better_string',
    'clean_error',
    'format_tb',
    'generate_error_objects',
    'generate_timestamp_string',
    'get_command_signature',
)


def better_string(data: Iterable[str | Any | None], *, seperator: str) -> str:
    return seperator.join(str(subdata) for subdata in data if subdata)


def generate_timestamp_string(dt: datetime.datetime) -> str:
    return f'{discord.utils.format_dt(dt, "D")} ({discord.utils.format_dt(dt, "R")})'


def clean_error(objects: list[str] | str, *, seperator: str, prefix: str) -> str:
    """
    Return a string with the given objects organised.

    Parameters
    ----------
    objects : list[str]
        List of iterables to prettify, this should be either list of roles or permissions.
    seperator : str
        String which seperates the given objects.
    prefix : str
        String which will be at the start of every object

    Returns
    -------
    str
        The generated string with the given parameters

    """
    return (
        better_string(
            (prefix + f'{(perm.replace("_", " ")).capitalize()}' for perm in objects),
            seperator=seperator,
        )
        if type(objects) is not str
        else prefix + objects
    )


def generate_error_objects(
    error: (
        commands.MissingPermissions
        | commands.BotMissingPermissions
        | commands.MissingAnyRole
        | commands.MissingRole
        | commands.BotMissingAnyRole
        | commands.BotMissingRole
    ),
) -> list[str] | str:
    """
    Generate a list or string of given objects from the error.

    Note
    ----
    Only to be used in error handler for these errors.


    Parameters
    ----------
    error : commands.MissingPermissions
      | commands.BotMissingPermissions
      | commands.MissingAnyRole
      | commands.MissingRole
      | commands.BotMissingAnyRole
      | commands.BotMissingRole
        The error used to make the objects

    Returns
    -------
    list[str] | str
        The list or string made from given errors.

    Raises
    ------
    ValueError
        Raised when the string was empty.

    """
    missing_role = (
        str(f'<@&{error.missing_role}>' if type(error.missing_role) is int else error.missing_role)
        if isinstance(error, commands.MissingRole | commands.BotMissingRole)
        else None
    )

    missing_roles = (
        [str(f'<@&{role_id}>' if role_id is int else role_id) for role_id in error.missing_roles]
        if isinstance(error, commands.MissingAnyRole | commands.BotMissingAnyRole)
        else None
    )

    missing_permissions = (
        error.missing_permissions
        if isinstance(error, commands.MissingPermissions | commands.BotMissingPermissions)
        else None
    )

    missings = missing_roles or missing_role or missing_permissions
    if not missings:
        msg = 'Expected Not-None value'
        raise ValueError(msg)

    return missings


class TimeConverter(commands.Converter[datetime.datetime]):
    async def convert(self, _: Context, argument: str) -> datetime.datetime:
        dt_obj: tuple[datetime.datetime, int] = parsedatetime.Calendar().parseDT(argument)  # pyright: ignore[reportAssignmentType, reportUnknownMemberType]

        if dt_obj[1] == 0:
            msg = 'Invalid time provided'
            raise commands.BadArgument(msg)

        if dt_obj[0] < datetime.datetime.now():
            msg = "The time you've provided is in the past"
            raise commands.BadArgument(msg)

        return dt_obj[0]


def format_tb(error: Exception) -> str:
    return ''.join(traceback.format_exception(type(error), error, error.__traceback__))


def get_command_signature(ctx: Context, command: commands.Command[Any, ..., Any], /) -> str:
    """
    Retrieve the signature portion of the help page.

    This is a modified copy of commands.HelpCommand.get_command_signature

    Parameters
    ----------
    ctx: :class:`Context`
        The context for this fetch.
    command: :class:`Command`
        The command to get the signature of.

    Returns
    -------
    :class:`str`
        The signature for the command.

    """
    parent: None | commands.Group[Any, ..., Any] = command.parent  # pyright: ignore[reportAssignmentType]
    entries: list[str] = []
    while parent is not None:
        if not parent.signature or parent.invoke_without_command:
            entries.append(parent.name)
        else:
            entries.append(parent.name + ' ' + parent.signature)
        parent = parent.parent  # pyright: ignore[reportAssignmentType]
    parent_sig = ' '.join(reversed(entries))

    alias = command.name if not parent_sig else parent_sig + ' ' + command.name

    return f'{ctx.clean_prefix}{alias} {command.signature}'
