from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Any

import discord

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from discord.ext import commands

    from utilities.bases.context import MafuContext


__all__ = (
    'fmt_str',
    'format_tb',
    'get_command_signature',
    'timestamp_str',
)


def fmt_str(data: Iterable[str | Any | None], *, seperator: str) -> str:
    """
    Return a string from an iterable ignoring any Falsy objects.

    Parameters
    ----------
    data : Iterable[str  |  Any  |  None]
        The iterable being used in the string
    seperator : str
        The string joining the iterables

    Returns
    -------
    str
        String produced from the given iterable and seperator

    """
    return seperator.join(str(subdata) for subdata in data if subdata)


def timestamp_str(dt: datetime, *, with_time: bool = False) -> str:
    return f'{discord.utils.format_dt(dt, "D" if with_time is False else "f")} ({discord.utils.format_dt(dt, "R")})'


def format_tb(error: Exception) -> str:
    return ''.join(traceback.format_exception(type(error), error, error.__traceback__))


def get_command_signature(ctx: MafuContext, command: commands.Command[Any, ..., Any], /) -> str:
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
