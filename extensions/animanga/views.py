from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Self

import discord
from asyncpg.exceptions import UniqueViolationError
from discord.ext import menus

from utils import (
    BaseView,
    BotEmojis,
    Embed,
    Paginator,
    WaifuNotFoundError,
    WaifuResult,
    better_string,
    generate_timestamp_string,
)
from utils.subclass import Mafuyu

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from utils import Context, Mafuyu, WaifuFavouriteEntry


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

        self.smash_emoji = self.smashbutton.emoji = BotEmojis.SMASH
        self.pass_emoji = self.passbutton.emoji = BotEmojis.PASS

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
        if await inst.ctx.bot.is_owner(ctx.author):
            inst.add_item(APIWaifuAddButton(inst.ctx))
        inst.message = await ctx.reply(embed=embed, view=inst)

        return inst

    async def request(self) -> WaifuResult:
        raise NotImplementedError

    def embed(self, data: WaifuResult) -> discord.Embed:
        smasher = better_string([user.mention for user in self.smashers], seperator=', ') or discord.utils.MISSING
        passer = better_string([user.mention for user in self.passers], seperator=', ') or discord.utils.MISSING

        total = len(self.passers) + len(self.smashers)

        r = round((len(self.passers) / total) * 255) if self.passers and total else 0
        g = round((len(self.smashers) / total) * 255) if self.smashers and total else 0
        colour = discord.Colour.from_rgb(r=r, g=g, b=0)

        embed = Embed(
            title=f'#{data.image_id}',
            url=f'https://danbooru.donmai.us/posts/{self.current.image_id}',
            description=better_string(
                [
                    f'- {self.smash_emoji} **Smashers:** {smasher}',
                    f'- {self.pass_emoji} **Passers:** {passer}',
                    f'-# **Characters:** {", ".join(data.parse_string_lists(data.characters))}' if data.characters else None,
                    f'-# **Copyright:** {", ".join(data.parse_string_lists(data.copyright))}' if data.copyright else None,
                ],
                seperator='\n',
            ),
            colour=colour,
            ctx=self.ctx,
        )

        embed.set_image(url=data.url)

        return embed

    @discord.ui.button(
        style=discord.ButtonStyle.green,
    )
    async def smashbutton(
        self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]
    ) -> discord.InteractionCallbackResponse[Mafuyu] | None:
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
    async def passbutton(
        self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]
    ) -> discord.InteractionCallbackResponse[Mafuyu] | None:
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
            return
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
                        self.query or '1girl',
                        'rating:' + rating,
                    ],
                    seperator=' ',
                ),
            },
        )
        data = await waifu.json()

        success = 200
        if waifu.status != success or not data:
            raise WaifuNotFoundError(self.query, json=data)

        current = WaifuResult(
            name=self.query,
            image_id=data['id'],
            url=data['file_url'],
            characters=data['tag_string_character'],
            copyright=data['tag_string_copyright'],
        )
        self.current = current

        return self.current


class WaifuPageSource(menus.ListPageSource):
    def __init__(self, bot: Mafuyu, entries: list[WaifuFavouriteEntry]) -> None:
        self.bot = bot
        super().__init__(entries, per_page=1)

    async def format_page(self, _: Paginator, entry: WaifuFavouriteEntry) -> Embed:
        post_url = f'https://danbooru.donmai.us/posts/{entry.id}.json'
        post_res = await self.bot.session.get(post_url)
        post_data = await post_res.json()

        post = WaifuResult(
            image_id=post_data['id'],
            url=post_data['file_url'],
            characters=post_data['tag_string_character'],
            copyright=post_data['tag_string_copyright'],
        )

        # We have the post and user's favourite data, basically everything

        embed = Embed(
            title=f'#{post.image_id} {"[NSFW]" if entry.nsfw is True else ""}',
            url=post_url,
            description=better_string(
                [
                    f'- **Favourited by:** {entry.user_id.mention}',
                    f'- **Favourited on:** {generate_timestamp_string(entry.tm)}',
                    f'-# **Characters:** {", ".join(post.parse_string_lists(post.characters))}' if post.characters else None,
                    f'-# **Copyright:** {", ".join(post.parse_string_lists(post.copyright))}' if post.copyright else None,
                ],
                seperator='\n',
            ),
            ctx=_.ctx,
        )
        embed.set_image(url=post.url)
        embed.set_thumbnail(url=entry.user_id.display_avatar.url)
        return embed


class RemoveFavButton(discord.ui.Button[Paginator]):
    view: Paginator

    def __init__(
        self,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.red,
    ) -> None:
        super().__init__(style=style, emoji=BotEmojis.RED_CROSS)

    async def callback(self, interaction: discord.Interaction[Mafuyu]) -> None:
        item: WaifuFavouriteEntry = await self.view.source.get_page(self.view.current_page)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        await interaction.client.pool.execute(
            """DELETE FROM WaifuFavourites WHERE id = $1 AND user_id = $2 RETURNING id""",
            item.id,  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
            interaction.user.id,
        )
        if hasattr(self.view.source, 'entries'):
            self.view.source.entries.pop(self.view.current_page)  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

            if self.view.source.entries:  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
                self.view.clear_items()
                self.view.fill_items()
                self.view.add_item(self)

                await self.view.show_checked_page(interaction, self.view.current_page)
                return
        await interaction.response.edit_message(content='No waifu favourite entries', embed=None, view=None)
        self.view.stop()


class APIWaifuAddButton(discord.ui.Button[WaifuBase]):
    view: WaifuBase

    def __init__(
        self,
        ctx: Context,
    ) -> None:
        self.ctx = ctx
        super().__init__(label='Add image to API', style=discord.ButtonStyle.blurple)

    async def interaction_check(self, interaction: discord.Interaction[Mafuyu]) -> bool:
        return bool(await self.ctx.bot.is_owner(interaction.user))

    async def callback(self, interaction: discord.Interaction[Mafuyu]) -> discord.InteractionCallbackResponse[Mafuyu]:
        waifu = self.view.current
        try:
            await interaction.client.pool.execute(
                """INSERT INTO
                        WaifuAPIEntries (file_url, added_by, nsfw)
                    VALUES
                        ($1, $2, $3)
                        """,
                waifu.url,
                interaction.user.id,
                self.view.nsfw,
            )
        except UniqueViolationError:
            await interaction.client.pool.execute("""DELETE FROM WaifuAPIEntries WHERE file_url = $1""", waifu.url)
            return await interaction.response.send_message(
                (
                    f'Successfully removed [#{waifu.image_id}]'
                    f'(<https://danbooru.donmai.us/posts/{waifu.image_id}>) to the API Image List'
                    f"\n-# If you don' know what it is, Ask {self.ctx.bot.owner.mention}"
                ),
                ephemeral=True,
            )

        return await interaction.response.send_message(
            (
                f'Successfully added [#{waifu.image_id}]'
                f'(<https://danbooru.donmai.us/posts/{waifu.image_id}>) to the API Image List'
                f"\n-# If you don' know what it is, Ask {self.ctx.bot.owner.mention}"
            ),
            ephemeral=True,
        )
