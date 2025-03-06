from __future__ import annotations

import inspect
import textwrap
from typing import TYPE_CHECKING, Any

from discord.ext import commands

from utils import BaseCog, BotEmojis, Context, format_tb

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Coroutine

    from discord import Message


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
            await self.bot.reload_extensions(str(self.bot.initial_extensions))
        except commands.ExtensionError as error:
            return await ctx.reply(format_tb(error))
        else:
            return await ctx.message.add_reaction(BotEmojis.GREEN_TICK)

    @commands.command(
        name='eval',
        aliases=['e'],
        help='Attempt at making an eval. Dont fucking use it with yields.',
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
        except Exception as err:  # noqa: BLE001
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
        except Exception as err:  # noqa: BLE001
            err_str = format_tb(err)
            return await ctx.reply(f'```py\n{err_str}```')
        return None
