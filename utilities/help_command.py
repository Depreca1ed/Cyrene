from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord.ext import commands

from utilities.constants import BotEmojis
from utilities.embed import Embed
from utilities.functions import fmt_str

if TYPE_CHECKING:
    from discord.app_commands import AppCommandContext, AppInstallationType
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

    def get_command_signature(self, command: commands.Command[Any, ..., Any]) -> str:
        parent: commands.Group[Any, ..., Any] | None = command.parent  # pyright: ignore[reportAssignmentType]
        entries: list[str] = []
        while parent is not None:
            if not parent.signature or parent.invoke_without_command:
                entries.append(parent.name)
            else:
                entries.append(parent.name + ' ' + parent.signature)
            parent = parent.parent  # pyright: ignore[reportAssignmentType]
        parent_sig = ' '.join(reversed(entries))

        if len(command.aliases) > 0:
            fmt = f'{command.name}'
            if parent_sig:
                fmt = parent_sig + ' ' + fmt
            alias = fmt
        else:
            alias = command.name if not parent_sig else parent_sig + ' ' + command.name

        return f'{self.context.clean_prefix}{alias} {command.signature}'

    def command_embed(self, command: commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any]) -> Embed:
        is_hybrid = isinstance(command, commands.HybridCommand)

        embed = Embed(title=command.qualified_name.title(), description=command.description)
        if command.help:
            embed.add_field(value=command.help)

        if is_hybrid and command.with_app_command is True and command.app_command:
            allowed_context = self._get_command_context(command.app_command)
            allowed_installs = self._get_command_installs(command.app_command)
            embed.add_field(
                name=f'{BotEmojis.SLASH} | Slash command',
                value=fmt_str(
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
        if command.aliases:
            embed.add_field(name='Aliases:', value=','.join([f'`{alias}`' for alias in command.aliases]))

        embed.add_field(name='Usage:', value=f'`{self.get_command_signature(command)}`')

        return embed

    async def send_command_help(self, command: commands.Command[Any, ..., Any]) -> None:
        await self.context.reply(embed=self.command_embed(command))
