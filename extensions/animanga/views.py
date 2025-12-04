from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Self, TypedDict

import discord
from asyncpg.exceptions import UniqueViolationError
from discord.ext import menus

from extensions.realmsphere.constants import RARITY_COLOURS
from extensions.realmsphere.types import CardFlags
from utilities.constants import BotEmojis
from utilities.embed import Embed
from utilities.errors import WaifuNotFoundError
from utilities.functions import fmt_str, timestamp_str
from utilities.pagination import Paginator
from utilities.types import WaifuFavouriteEntry, WaifuResult
from utilities.view import BaseView

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from utilities.bases.bot import Cyrene
    from utilities.bases.context import CyContext

__all__ = ('WaifuSearchView',)


class WaifuBase(BaseView):
    ctx: CyContext
    current: WaifuResult

    def __init__(
        self,
        ctx: CyContext,
        session: ClientSession,
        *,
        nsfw: bool,
        for_user: int,
        query: None | str = None,
    ) -> None:
        super().__init__()
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
    async def start(cls, ctx: CyContext, *, query: None | str = None) -> Self | None:
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
        try:
            data = await inst.request()
        except KeyError:
            await ctx.reply('Hey! The bot got ratelimited by danbooru. Try again')
            return None

        embed = inst.embed(data)

        inst.ctx = ctx

        if await inst.ctx.bot.is_owner(ctx.author):
            inst.add_item(RealmSphereWaifuAddButton(inst.ctx))

        inst.message = await ctx.reply(embed=embed, view=inst)

        return inst

    async def request(self) -> WaifuResult:
        raise NotImplementedError

    def embed(self, data: WaifuResult) -> discord.Embed:
        smasher = fmt_str([user.mention for user in self.smashers], seperator=', ') or discord.utils.MISSING
        passer = fmt_str([user.mention for user in self.passers], seperator=', ') or discord.utils.MISSING

        total = len(self.passers) + len(self.smashers)

        r = round((len(self.passers) / total) * 255) if self.passers and total else 0
        g = round((len(self.smashers) / total) * 255) if self.smashers and total else 0
        colour = discord.Colour.from_rgb(r=r, g=g, b=0)

        embed = Embed(
            title=f'#{data.image_id}',
            url=f'https://danbooru.donmai.us/posts/{self.current.image_id}',
            description=fmt_str(
                [
                    f'- {self.smash_emoji} **Smashers:** {smasher}',
                    f'- {self.pass_emoji} **Passers:** {passer}',
                    f'-# **Characters:** {", ".join(data.parse_string_lists(data.characters))}' if data.characters else None,
                    f'-# **Copyright:** {", ".join(data.parse_string_lists(data.copyright))}' if data.copyright else None,
                ],
                seperator='\n',
            ),
            colour=colour,
        )

        embed.set_image(url=data.url)

        if self.nsfw:
            embed.set_footer(text='For SFW results, run this command in a SFW channel.')

        return embed

    @discord.ui.button(
        style=discord.ButtonStyle.green,
    )
    async def smashbutton(
        self, interaction: discord.Interaction[Cyrene], _: discord.ui.Button[Self]
    ) -> discord.InteractionCallbackResponse[Cyrene] | None:
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
        self, interaction: discord.Interaction[Cyrene], _: discord.ui.Button[Self]
    ) -> discord.InteractionCallbackResponse[Cyrene] | None:
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
    async def _next(self, interaction: discord.Interaction[Cyrene], _: discord.ui.Button[Self]) -> None:
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
        rating = fmt_str(['explicit', 'questionable', 'sensitive'], seperator=',') if self.nsfw is True else 'general'
        waifu = await self.session.get(
            'https://danbooru.donmai.us/posts/random.json',
            params={
                'tags': fmt_str(
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
            source=data['source'],
            characters=data['tag_string_character'],
            copyright=data['tag_string_copyright'],
        )
        self.current = current

        return self.current


class WaifuPageSource(menus.ListPageSource):
    def __init__(self, bot: Cyrene, entries: list[WaifuFavouriteEntry]) -> None:
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
            description=fmt_str(
                [
                    f'- **Favourited by:** {entry.user_id.mention}',
                    f'- **Favourited on:** {timestamp_str(entry.tm, with_time=True)}',
                    f'-# **Characters:** {", ".join(post.parse_string_lists(post.characters))}' if post.characters else None,
                    f'-# **Copyright:** {", ".join(post.parse_string_lists(post.copyright))}' if post.copyright else None,
                ],
                seperator='\n',
            ),
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
        super().__init__(
            style=style,
            emoji=BotEmojis.RED_CROSS,
            label='Remove entry',
        )

    async def callback(self, interaction: discord.Interaction[Cyrene]) -> None:
        item: WaifuFavouriteEntry = await self.view.source.get_page(self.view.current_page)  # pyright: ignore[reportUnknownMemberType]
        await interaction.client.pool.execute(
            """DELETE FROM WaifuFavourites WHERE id = $1 AND user_id = $2 RETURNING id""",
            item.id,  # pyright: ignore[reportUnknownMemberType]
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


class RealmSphereWaifuAddButton(discord.ui.Button[WaifuBase]):
    view: WaifuBase

    def __init__(
        self,
        ctx: CyContext,
    ) -> None:
        self.ctx = ctx
        super().__init__(label='Add image to Realm Sphere', style=discord.ButtonStyle.blurple)

    async def interaction_check(self, interaction: discord.Interaction[Cyrene]) -> bool:
        return bool(await self.ctx.bot.is_owner(interaction.user))

    async def callback(self, interaction: discord.Interaction[Cyrene]) -> None:
        waifu = self.view.current

        v = CardCreationView(waifu)
        await interaction.response.send_message(view=v)


class PartialCardData(TypedDict):
    name: str | None
    rarity: int
    characters: str


class CardCreationView(discord.ui.LayoutView):
    control_buttons = discord.ui.ActionRow()

    def __init__(self, waifu_data: WaifuResult) -> None:
        self.waifu_data = waifu_data
        self.data: PartialCardData = {
            'name': self.waifu_data.parse_string_lists(self.waifu_data.characters)[0],
            'rarity': 0,
            'characters': self.waifu_data.characters,
        }
        self.creation_logs: list[str] = []
        self.completed: bool = False
        super().__init__()
        self.display()

    def display(self) -> None:
        self.clear_items()

        container = discord.ui.Container(
            accent_color=0xFFFFFF if not self.data.get('rarity') else RARITY_COLOURS[int(self.data['rarity'])]
        )

        container.add_item(discord.ui.TextDisplay('## Card Creation via Danbooru'))

        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    fmt_str(
                        (f'- **{k.title()}:** {v}' for k, v in self.data.items()),
                        seperator='\n',
                    )
                ),
                accessory=EditInfoButton(self.data),
            )
        )

        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(self.waifu_data.url)))

        if self.creation_logs:
            container.add_item(discord.ui.Separator())

            container.add_item(discord.ui.TextDisplay('```\n' + '\n'.join(self.creation_logs) + '```'))

        container.add_item(discord.ui.Separator())

        if self.completed is False:
            container.add_item(self.control_buttons)  # pyright: ignore[reportUnknownMemberType]

        self.add_item(container)

    @control_buttons.button(label='Create card', style=discord.ButtonStyle.green, emoji=BotEmojis.GREEN_TICK)
    async def create_card(
        self, interaction: discord.Interaction[Cyrene], _: discord.ui.Button[Self]
    ) -> discord.InteractionCallbackResponse[Cyrene] | None:
        self.creation_logs.append('[INFO] Starting creation')

        name = self.data['name']
        self.creation_logs.append(f'[INFO] Name: {name}')

        rarity = int(self.data['rarity'])
        self.creation_logs.append(f'[INFO] Rarity: {rarity}')

        characters = self.waifu_data.parse_string_lists(self.data['characters'])
        self.creation_logs.append(f'[INFO] Characters: {", ".join(characters)}')

        card_data = await interaction.client.pool.fetchrow(
            """
            INSERT INTO Cards (card_name, rarity, flag)
            VALUES ($1, $2, $3)
            RETURNING *;
            """,
            name,
            rarity,
            CardFlags.NORMAL,
        )
        if not card_data:
            self.creation_logs.append('[ERROR] Insertion returned None')
            self.display()
            return await interaction.response.edit_message(view=self)

        card_id = card_data['id']
        self.creation_logs.append(f'[INFO] Card created with ID: {card_id}')

        for character in characters:
            await interaction.client.pool.execute(
                """INSERT INTO CardCharactersRelation VALUES ($1, $2);""",
                card_id,
                character,
            )
        self.creation_logs.append('[INFO] Character relations created')

        self.completed = True

        self.display()

        return await interaction.response.edit_message(view=self)


class EditInfoButton(discord.ui.Button[CardCreationView]):
    view: CardCreationView

    def __init__(self, data: PartialCardData) -> None:
        self.data = data
        super().__init__(
            style=discord.ButtonStyle.gray,
            emoji='\U0000270d',
        )

    async def callback(self, interaction: discord.Interaction[Cyrene]) -> None:
        modal = EditModal(self.view, self.data)
        await interaction.response.send_modal(modal)


class EditModal(discord.ui.Modal, title='Edit data'):
    def __init__(self, view: CardCreationView, data: PartialCardData) -> None:
        self.view = view
        self.data = data

        super().__init__()
        for k, v in self.data.items():
            self.add_item(
                discord.ui.Label(
                    text=k,
                    component=discord.ui.TextInput(default=str(v) if v is not None else None),
                )
            )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        for child in self.children:
            assert isinstance(child, discord.ui.Label)

            label_input = child.component
            assert isinstance(label_input, discord.ui.TextInput)

            self.view.data[child.text] = label_input.value

        self.view.display()
        await interaction.response.edit_message(view=self.view)
