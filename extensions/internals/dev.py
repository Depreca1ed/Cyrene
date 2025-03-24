from __future__ import annotations

import inspect
import textwrap
from typing import TYPE_CHECKING, Any

from discord.ext import commands

from utils import BaseCog, BotEmojis, format_tb

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Coroutine, Iterable

    import discord
    from discord import Message

    from utils import Context

PERMISSIONS_STRUCTURE = {
    'general': [
        'view_channels',
        'manage_channels',
        'manage_roles',
        'create_expressions',
        'manage_expressions',
        'view_audit_log',
        'view_server_insights',
        'manage_webhooks',
        'manage_server',
    ],
    'membership': [
        'create_invite',
        'change_nickname',
        'manage_nicknames',
        'kick_members',
        'ban_members',
        'moderate_members',
    ],
    'text': [
        'send_messsages',
        'send_messages_in_threads',
        'create_public_threads',
        'create_private_threads',
        'embed_links',
        'attach_files',
        'add_reactions',
        'use_external_emojis',
        'use_external_stickers',
        'use_external_sounds',
        'mention_everyone',
        'manage_messages',
        'manage_threads',
        'read_message_history',
        'send_tts',
        'send_voice_messages',
        'create_polls',
    ],
    'voice': [
        'connect',
        'speak',
        'video',
        'use_soundboard',
        'use_external_sounds',
        'use_voice_activity',
        'priority_speaking',
        'mute_memebrs',
        'deafen_members',
        'move_members',
        'set_voice_channel_status',
    ],
    'apps': [
        'use_application_commands',
        'use_activities',
        'use_external_apps',
    ],
    'events': [
        'create_events',
        'manage_events',
    ],
    'misc': [
        'request_to_speak',
        'administrator',
    ],
}


def get_permission_emoji(
    *, permissions: Iterable[bool] | None = None, permission: bool | None = None
) -> discord.PartialEmoji:
    if permissions:
        if all_true_or_false(permissions) is True:
            return BotEmojis.GREEN_TICK
        if all_true_or_false(permissions) is False:
            return BotEmojis.RED_CROSS
        return BotEmojis.GREY_TICK
    return BotEmojis.GREEN_TICK if permission and permission is True else BotEmojis.RED_CROSS


def all_true_or_false(targets: Iterable[bool]) -> None | bool:
    if all(targets):
        return True
    if not [_ for _ in targets if _ is True]:
        return False
    return None


def p_string(
    p: str,
) -> str:
    return f' | `{p.replace("_", " ").title()}`'


class Developer(BaseCog):
    def _cleanup_code(self, code: str) -> str:
        if code.startswith('```') and code.endswith('```'):
            code = '\n'.join(code.split('\n')[1:])
            return code.removesuffix('```')

        return code.strip('` \n')

    def _add_return(self, code: str) -> str:
        code_lines = code.split('\n')
        has_yield = [line for line in code_lines if line.startswith('yield ')]
        code_lines[-1] = (
            f'{"return" if not has_yield else "yield "} ' + code_lines[-1]
            if not code_lines[-1].startswith('return ')
            else code_lines[-1]
        )
        return '\n'.join(code_lines)

    @commands.command(name='reload', aliases=['re'], hidden=True)
    async def reload_cogs(self, ctx: Context) -> None | Message:
        try:
            await self.bot.reload_extensions(self.bot.initial_extensions)
        except commands.ExtensionError as error:
            return await ctx.reply(format_tb(error))
        else:
            return await ctx.message.add_reaction(BotEmojis.GREEN_TICK)

    @commands.command(
        name='eval',
        aliases=['e'],
        description='Attempt at making an eval. Dont fucking use it with yields.',
    )
    async def eval(self, ctx: Context, *, code: str) -> Message | None:
        variables: dict[str, Any] = {
            'bot': self.bot,
            'ctx': ctx,
            'author': ctx.author,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'reference': ctx.message.reference,
            'ref': ctx.message.reference,
            'message': ctx.message,
            'msg': ctx.message,
        }
        variables.update(globals())

        code = self._cleanup_code(code)
        code = self._add_return(code)

        the_actual_code = f'async def run_code():\n{textwrap.indent(code, "    ")}'

        try:
            exec(the_actual_code, variables)  # noqa: S102
        except Exception as err:
            err_str = format_tb(err)
            return await ctx.reply(f'```py\n{err_str}```')

        function: Coroutine[Any, Any, Any] | AsyncGenerator[Any, Any] = variables['run_code']
        try:
            if inspect.iscoroutinefunction(function):
                returns: Any = await function()
                return await ctx.reply(str(returns))

            if inspect.isasyncgenfunction(function):
                async for ret in function():
                    await ctx.send(ret)
        except Exception as err:
            err_str = format_tb(err)
            return await ctx.reply(f'```py\n{err_str}```')
        return None
