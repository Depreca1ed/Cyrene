from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Self

import discord
from asyncpg.exceptions import UniqueViolationError

from utils import BaseView, Embed, WaifuNotFoundError, WaifuResult, better_string

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from utils import Context, Mafuyu


__all__ = ('WaifuSearchView',)


class WaifuBase(BaseView):
    ctx: Context
    current: WaifuResult

    def __init__(
        self,
        ctx: Context,
        session: ClientSession,
        *,
        nsfw: bool,
        for_user: int,
        query: None | str = None,
    ) -> None:
        super().__init__(timeout=500.0)
        self.ctx = ctx
        self.session = session
        self.nsfw = nsfw
        self.for_user = for_user
        self.query = query

        self.smashers: set[discord.User | discord.Member] = set()
        self.passers: set[discord.User | discord.Member] = set()

        self.smash_emoji = self.smashbutton.emoji = self.ctx.bot.bot_emojis['SMASH']
        self.pass_emoji = self.passbutton.emoji = self.ctx.bot.bot_emojis['PASS']

    @classmethod
    async def start(cls, ctx: Context, *, query: None | str = None) -> Self | None:
        inst = cls(
            ctx,
            ctx.bot.session,
            for_user=ctx.author.id,
            nsfw=(
                ctx.channel.is_nsfw()
                if not isinstance(
                    ctx.channel,
                    discord.DMChannel | discord.GroupChannel | discord.PartialMessageable,
                )
                else False
            ),
            query=query,
        )
        data = await inst.request()

        embed = inst.embed(data)

        inst.ctx = ctx
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
                    f'- {self.smash_emoji} **Smashers:** {smasher}',
                    f'- {self.pass_emoji} **Passers:** {passer}',
                    '',
                    f'-# Characters: {" ".join(data.parse_string_lists(data.characters))}',
                    f'-# Copyright: {" ".join(data.parse_string_lists(data.copyright))}',
                ],
                seperator='\n',
            ),
            ctx=self.ctx,
        )

        embed.set_image(url=data.url)

        return embed

    @discord.ui.button(
        style=discord.ButtonStyle.green,
    )
    async def smashbutton(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        if interaction.user in self.smashers:
            try:
                await interaction.client.pool.execute(
                    """INSERT INTO WaifuFavourites VALUES ($1, $2, $3, $4)""",
                    self.current.image_id,
                    interaction.user.id,
                    self.nsfw,
                    datetime.datetime.now(),
                )
            except UniqueViolationError:
                return await interaction.response.send_message(
                    'You have already added this waifu in your favourites list',
                    ephemeral=True,
                )
            return await interaction.response.send_message(
                (
                    f'Successfully added [#{self.current.image_id}]'
                    f'(<https://danbooru.donmai.us/posts/{self.current.image_id}>) to your favourites!'
                ),
                ephemeral=True,
            )

        if interaction.user in self.passers:
            self.passers.remove(interaction.user)

        self.smashers.add(interaction.user)
        await interaction.client.pool.execute(
            """
                INSERT INTO
                    Waifus (id, smashes, nsfw)
                VALUES
                    ($1, 1, $2)
                ON CONFLICT (id) DO
                UPDATE
                SET
                    smashes = Waifus.smashes + 1
            """,
            self.current.image_id,
            self.nsfw,
        )
        await interaction.response.edit_message(embed=self.embed(self.current))
        return None

    @discord.ui.button(
        style=discord.ButtonStyle.red,
    )
    async def passbutton(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        if interaction.user in self.passers:
            results = await interaction.client.pool.fetch(
                """DELETE FROM WaifuFavourites WHERE id = $1 AND user_id = $2 RETURNING id""",
                self.current.image_id,
                interaction.user.id,
            )
            if results:
                return await interaction.response.send_message(
                    (
                        f'Successfully removed [#{self.current.image_id}]'
                        f'(<https://danbooru.donmai.us/posts/{self.current.image_id}>) to your favourites!'
                    ),
                    ephemeral=True,
                )
        if interaction.user in self.smashers:
            self.smashers.remove(interaction.user)

        self.passers.add(interaction.user)
        await interaction.client.pool.execute(
            """
                INSERT INTO
                    Waifus (id, passes, nsfw)
                VALUES
                    ($1, 1, $2)
                ON CONFLICT (id) DO
                UPDATE
                SET
                    passes = Waifus.passes + 1
                """,
            self.current.image_id,
            self.nsfw,
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


class WaifuSearchView(WaifuBase):
    async def request(self) -> WaifuResult:
        rating = better_string(['explicit', 'questionable', 'sensitive'], seperator=',') if self.nsfw is True else 'general'
        waifu = await self.session.get(
            'https://danbooru.donmai.us/posts/random.json',
            params={
                'tags': better_string(
                    [
                        'solo',
                        self.query or '',
                        'rating:' + rating,
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
            source=data['source'],
            url=data['file_url'],
            characters=data['tag_string_character'],
            copyright=data['tag_string_copyright'],
        )
        self.current = current

        return self.current
