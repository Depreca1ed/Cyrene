from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, WaifuNotFoundError

from .views import WaifuSearchView

if TYPE_CHECKING:
    import aiohttp

    from utils import Context, Mafuyu

__all__ = ('Waifu',)

CHARACTER_ID = 4


async def get_waifu(session: aiohttp.ClientSession, waifu: str) -> list[tuple[str, str]]:
    req = await session.get(
        'https://safebooru.donmai.us/autocomplete.json',
        params={
            'search[query]': waifu,
            'search[type]': 'tag_query',
        },
    )
    data = await req.json()
    characters = [
        (str(obj['label']), str(obj['value']))
        for obj in data
        if obj['type'] == 'tag-word' and obj.get('category') == CHARACTER_ID
    ]
    if req.status != 200 or not data or not characters:
        raise WaifuNotFoundError(waifu)
    return characters


async def waifu_autocomplete(
    interaction: discord.Interaction[Mafuyu],
    current: str,
) -> list[app_commands.Choice[str]]:
    try:
        characters = await get_waifu(interaction.client.session, current)
    except WaifuNotFoundError:
        return []
    return [app_commands.Choice(name=char[0].title(), value=char[1]) for char in characters]


class Waifu(BaseCog):
    @commands.hybrid_group(name='waifu', help='Get waifu images with an option to smash or pass', fallback='get')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.autocomplete(waifu=waifu_autocomplete)
    async def waifu(self, ctx: Context, *, waifu: str | None) -> None:
        if waifu:
            waifu = waifu.replace(' ', '_')
            characters = await get_waifu(ctx.bot.session, waifu)
            waifu = characters[0][1]  # Points to the value of the first result
        await WaifuSearchView.start(ctx, query=waifu)

    @waifu.command(name='favourites', with_app_command=False, disabled=True)
    @commands.is_owner()
    async def waifu_favourites(self, ctx: Context) -> None:
        await ctx.reply('test')
