from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utilities.bases.cog import MafuCog
from utilities.errors import WaifuNotFoundError
from utilities.pagination import Paginator
from utilities.types import WaifuFavouriteEntry

from .views import RemoveFavButton, WaifuPageSource, WaifuSearchView

if TYPE_CHECKING:
    import aiohttp

    from utilities.bases.bot import Mafuyu
    from utilities.bases.context import MafuContext


__all__ = ('Waifu',)

TAG_ALLOWED_TYPES = [3, 4]


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
        if obj['type'] == 'tag-word' and obj.get('category') in TAG_ALLOWED_TYPES
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


class Waifu(MafuCog):
    @commands.hybrid_group(name='waifu', help='Get waifu images with an option to smash or pass', fallback='get')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.autocomplete(waifu=waifu_autocomplete)
    async def waifu(self, ctx: MafuContext, *, waifu: str | None) -> None:
        if waifu:
            waifu = waifu.replace(' ', '_')
            characters = await get_waifu(ctx.bot.session, waifu)
            waifu = characters[0][1]  # Points to the value of the first result
        await WaifuSearchView.start(ctx, query=waifu)

    @waifu.command(name='favourites', help="Get your or user's favourited waifus", aliases=['fav'], with_app_command=True)
    async def waifu_favourites(self, ctx: MafuContext, user: discord.User = commands.Author) -> None:
        show_nsfw = (
            ctx.channel.is_nsfw()
            if not isinstance(
                ctx.channel,
                discord.DMChannel | discord.GroupChannel | discord.PartialMessageable,
            )
            else False
        )

        query = """SELECT * FROM WaifuFavourites WHERE user_id = $1""" + (' AND nsfw = $2' if show_nsfw is False else '')  # noqa: S608
        args = [
            user.id,
        ]

        if show_nsfw is False:
            args.append(show_nsfw)
        fav_entries = await self.bot.pool.fetch(
            query,
            *args,
        )

        if not fav_entries:
            await ctx.reply(
                'No waifu favourites entry found.\n-# You can favourite a waifu by pressing the smash button twice'
            )
            return

        fav_parsed = [WaifuFavouriteEntry(id=e['id'], user_id=user, nsfw=e['nsfw'], tm=e['tm']) for e in fav_entries]

        paginate = Paginator(WaifuPageSource(self.bot, entries=fav_parsed), ctx=ctx)
        paginate.add_item(RemoveFavButton())
        await paginate.start()
