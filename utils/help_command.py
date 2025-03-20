from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord.app_commands import AppCommandContext, AppInstallationType
from discord.ext import commands

from utils.constants import BotEmojis
from utils.embed import Embed
from utils.helper_functions import better_string

if TYPE_CHECKING:
    from discord.ext.commands.hybrid import HybridAppCommand  # pyright: ignore[reportMissingTypeStubs]


class MafuHelpCommand(commands.HelpCommand):
    def _get_command_context(self, command: HybridAppCommand[Any, ..., Any]) -> AppCommandContext | None:
        if command.allowed_contexts:
            return command.allowed_contexts

        parent = command.parent
        while parent is not None:
            c = parent.allowed_contexts
            if c:
                return c
            parent = parent.parent
        return None

    def _get_command_installs(self, command: HybridAppCommand[Any, ..., Any]) -> AppInstallationType | None:
        if command.allowed_installs:
            return command.allowed_installs

        parent = command.parent
        while parent is not None:
            c = parent.allowed_installs
            if c:
                return c
            parent = parent.parent
        return None

    def _get_context_strings(self, context: AppCommandContext) -> list[str]:
        return [
            _
            for _ in [
                'Direct Messages' if context.dm_channel is True else None,
                'Server Channels' if context.guild is True else None,
                'Private Channels' if context.private_channel is True else None,
            ]
            if _ is not None
        ]

    def _get_installs_strings(self, installs: AppInstallationType) -> list[str]:
        return [
            _
            for _ in [
                'Users' if installs.user is True else None,
                'Servers' if installs.guild is True else None,
            ]
            if _ is not None
        ]

    async def send_command_help(
        self, command: commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any]
    ) -> None:
        is_hybrid = isinstance(command, commands.HybridCommand)

        embed = Embed(title=command.name.title(), description=command.description)
        if command.help:
            embed.add_field(value=command.help)

        if is_hybrid and command.with_app_command is True and command.app_command:
            allowed_context = self._get_command_context(command.app_command)
            allowed_installs = self._get_command_installs(command.app_command)
            embed.add_field(
                name=f'{BotEmojis.SLASH} | Slash command',
                value=better_string(
                    [
                        '- **Can run in :** ' + ', '.join(self._get_context_strings(allowed_context))
                        if allowed_context
                        else None,
                        '- **Installable to :** ' + ', '.join(self._get_installs_strings(allowed_installs))
                        if allowed_installs
                        else None,
                    ],
                    seperator='\n',
                ),
            )

        await self.context.reply(embed=embed)
