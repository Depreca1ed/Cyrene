from __future__ import annotations

from typing import TYPE_CHECKING, Self

import discord
from asyncpg.exceptions import UniqueViolationError

from utils import BaseView, Context, Embed, WaifuNotFoundError, WaifuResult, better_string

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from bot import Mafuyu


__all__ = ('WaifuSearchView',)


class SmashOrPass(BaseView):
    message: discord.Message | None
    ctx: Context
    current: WaifuResult
    token: str

    def __init__(
        self,
        session: ClientSession,
        *,
        for_user: int,
        nsfw: bool,
        source: str,
        query: None | str = None,
    ) -> None:
        super().__init__(timeout=500.0)
        self.session = session
        self.for_user = for_user
        self.nsfw = nsfw
        self.source = source
        self.query = query

        self.smashers: set[discord.User | discord.Member] = set()
        self.passers: set[discord.User | discord.Member] = set()

    @classmethod
    async def start(cls, ctx: Context, source: str, *, query: None | str = None) -> Self | None:
        inst = cls(
            ctx.bot.session,
            for_user=ctx.author.id,
            nsfw=ctx.channel.is_nsfw()
            if not isinstance(ctx.channel, discord.DMChannel | discord.GroupChannel | discord.PartialMessageable)
            else False,
            source=source,
            query=query,
        )
        inst.token = ctx.bot.config.WAIFU_TOKEN
        inst.ctx = ctx
        data = await inst.request()

        embed = inst.embed(data)
        inst.message = await ctx.reply(embed=embed, view=inst)

        return inst

    async def request(self) -> WaifuResult:
        raise NotImplementedError

    def embed(self, data: WaifuResult) -> discord.Embed:
        smasher = better_string([user.mention for user in self.smashers], seperator=', ') or discord.utils.MISSING
        passer = better_string([user.mention for user in self.passers], seperator=', ') or discord.utils.MISSING

        embed = Embed(
            title='Smash or Pass',
            description=better_string(
                [
                    (f'> [#{data.image_id}]({data.source})' if data.image_id and data.source else None),
                    f'- <:MafuyuBlush:1314149745794617365> **Smashers:** {smasher}',
                    f'- <:MafuyuUnamused:1314149535043293215> **Passers:** {passer}',
                ],
                seperator='\n',
            ),
            colour=(discord.Colour.from_str(data.dominant_color) if data.dominant_color else None),
            ctx=self.ctx,
        )

        embed.set_image(url=data.url)

        return embed

    @discord.ui.button(
        emoji='<:MafuyuBlush:1314149745794617365>',
        style=discord.ButtonStyle.green,
    )
    async def smash(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        if interaction.user in self.smashers:
            try:
                await interaction.client.pool.execute(
                    """INSERT INTO WaifuFavourites VALUES ($1, $2, $3)""",
                    self.current.url,
                    interaction.user.id,
                    self.nsfw,
                )
            except UniqueViolationError:
                return await interaction.response.send_message(
                    'You have already added this waifu in your favourites list',
                    ephemeral=True,
                )
            return await interaction.response.send_message(
                f'Successfully added [#{self.current.image_id}](<{self.current.url}>) to your favourites!',
                ephemeral=True,
            )

        if interaction.user in self.passers:
            self.passers.remove(interaction.user)

        self.smashers.add(interaction.user)
        await interaction.client.pool.execute(
            """
                INSERT INTO
                    Waifus (id, smashes, nsfw, type)
                VALUES
                    ($1, 1, $2, $3)
                ON CONFLICT (id, type) DO
                UPDATE
                SET
                    smashes = Waifus.smashes + 1
            """,
            self.current.image_id,
            self.nsfw,
            self.source,
        )
        await interaction.response.edit_message(embed=self.embed(self.current))
        return None

    @discord.ui.button(
        emoji='<:MafuyuUnamused:1314149535043293215>',
        style=discord.ButtonStyle.red,
    )
    async def passbutton(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        if interaction.user in self.passers:
            return await interaction.response.defer()

        if interaction.user in self.smashers:
            self.smashers.remove(interaction.user)

        self.passers.add(interaction.user)
        await interaction.client.pool.execute(
            """
                INSERT INTO
                    Waifus (id, passes, nsfw, type)
                VALUES
                    ($1, 1, $2, $3)
                ON CONFLICT (id, type) DO
                UPDATE
                SET
                    passes = Waifus.passes + 1
                """,
            self.current.image_id,
            self.nsfw,
            self.source,
        )
        await interaction.response.edit_message(embed=self.embed(self.current))
        return None

    @discord.ui.button(emoji='🔁', style=discord.ButtonStyle.grey)
    async def _next(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        self.smashers.clear()
        self.passers.clear()
        try:
            data = await self.request()
        except KeyError:
            await interaction.response.send_message('Hey! Slow down.', ephemeral=True)
        else:
            await interaction.response.edit_message(embed=self.embed(data))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.for_user:
            return True

        if (
            interaction.user.id != self.for_user
            and interaction.data
            and interaction.data.get('custom_id') == self._next.custom_id
        ):
            await interaction.response.send_message(
                'Only the command initiator can cycle through waifus in this message.',
                ephemeral=True,
            )

            return False

        return True


class WaifuSearchView(SmashOrPass):
    async def request(self) -> WaifuResult:
        waifu = await self.session.get(
            'https://danbooru.donmai.us/posts/random.json',
            params={
                'tags': better_string(
                    [
                        'solo',
                        self.query or '',
                        'rating:'
                        + (
                            better_string(['explicit', 'questionable', 'sensitive'], seperator=',')
                            if self.nsfw is True
                            else 'general'
                        ),
                    ],
                    seperator=' ',
                ),
            },
        )
        data = await waifu.json()
        success = 200
        if waifu.status != success or not data:
            raise WaifuNotFoundError(self.query)
        current = WaifuResult(
            name=self.query,
            image_id=data['id'],
            dominant_color=None,
            source=data['source'],
            url=data['file_url'],
        )
        self.current = current

        return self.current
