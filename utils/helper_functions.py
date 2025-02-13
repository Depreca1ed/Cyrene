from __future__ import annotations

import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

    from . import Context, Mafuyu


__all__ = ('better_string',)


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
        if objects is not str
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
    missing_roles = (
        [str(f'<@&{role_id}>' if role_id is int else role_id) for role_id in error.missing_roles]
        if isinstance(error, commands.MissingAnyRole | commands.BotMissingAnyRole)
        else None
    )

    missing_role = (
        str(f'<@&{error.missing_role}>' if error.missing_role is int else error.missing_role)
        if isinstance(error, commands.MissingRole | commands.BotMissingRole)
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


def format_tb(bot: Mafuyu, error: Exception) -> str:
    return ''.join(traceback.format_exception(type(error), error, error.__traceback__)).replace(
        str(Path.cwd()), f'/{bot.user.name}'
    )


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
