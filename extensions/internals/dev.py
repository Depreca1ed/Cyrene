from __future__ import annotations

from discord.ext import commands

from utils import BaseCog, Context, better_string


class Developer(BaseCog):
    @commands.command(name='reload', aliases=['re'], hidden=True)
    async def reload_cogs(self, ctx: Context) -> None:
        exts = self.bot.initial_extensions
        messages: list[str] = []

        for ext in exts:
            try:
                await self.bot.reload_extension(str(ext))
            except commands.ExtensionError as error:
                messages.append(f'Failed to reload {ext}\n```py{error}```')
            else:
                messages.append(f'Reloaded {ext}')

        await ctx.send(content=better_string(messages, seperator='\n'))

    @commands.command(name='eval', aliases=['e'], help='Evaluate code')
    async def eval(self, ctx: Context, code: str) -> None:
        result = exec(code)  # noqa: S102
        await ctx.reply(result)
