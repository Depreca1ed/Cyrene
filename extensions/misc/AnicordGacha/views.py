from __future__ import annotations

import datetime
import operator
from typing import TYPE_CHECKING, Self

import discord
import humanize
from discord.ext import menus

from extensions.misc.AnicordGacha.bases import GachaUser, PulledCard, PullSource
from extensions.misc.AnicordGacha.constants import RARITY_EMOJIS
from extensions.misc.AnicordGacha.utils import get_burn_worths
from utilities.bases.bot import Elysia
from utilities.constants import BotEmojis
from utilities.embed import Embed
from utilities.functions import fmt_str, timestamp_str
from utilities.pagination import Paginator
from utilities.timers import ReservedTimerType
from utilities.view import BaseView

if TYPE_CHECKING:
    from utilities.bases.bot import Elysia
    from utilities.bases.context import ElyContext


def _switch(v: bool) -> discord.PartialEmoji:  # noqa: FBT001
    return BotEmojis.ON_SWITCH if v is True else BotEmojis.OFF_SWITCH


class GachaPullView(BaseView):
    def __init__(
        self,
        ctx: ElyContext,
        user: discord.User | discord.Member,
        gacha_user: GachaUser,
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.user = user
        self.gacha_user = gacha_user

        self.update_display()

    @classmethod
    async def start(
        cls,
        ctx: ElyContext,
        *,
        user: discord.User | discord.Member,
    ) -> discord.InteractionCallbackResponse[Elysia] | discord.Message | None:
        gacha_user = await GachaUser.from_fetched_record(ctx.bot.pool, user=user)

        c = cls(ctx, user, gacha_user)

        embed = c.embed()

        return await ctx.reply(embed=embed, view=c)

    def embed(self) -> Embed:
        embed = Embed(colour=self.user.color)

        s: list[str] = []

        if self.gacha_user.timer is None:
            s.append('- You do not have a pull reminder setup yet.')
        else:
            next_pull = self.gacha_user.timer.expires
            s.append(f'> **Next Pull :** {timestamp_str(next_pull, with_time=True)}')

        config: list[str] = []

        config.extend((
            f'### {_switch(self.gacha_user.config_data["autoremind"])} > Auto remind',
            f'### {_switch(bool(self.gacha_user.config_data["custom_remind_message"]))} > Custom remind message',
            f'### {_switch(self.gacha_user.config_data["custom_pull_reaction"])} > Custom pull reaction',
        ))

        embed.description = fmt_str(s, seperator='\n') + '\n' + fmt_str(config, seperator='\n')

        return embed

    def update_display(self) -> None:
        self.clear_items()
        self.add_item(self.primary_select)

        options: list[discord.SelectOption] = []

        if self.gacha_user.timer is not None:
            options.append(
                discord.SelectOption(
                    label='Cancel reminder',
                    value='cancel_reminder',
                    emoji=BotEmojis.SLASH,
                    description='Scheduled to remind in '
                    + humanize.naturaldelta(
                        self.gacha_user.timer.expires - discord.utils.utcnow(),
                    ),
                )
            )
        options.extend((
            discord.SelectOption(
                label='Automatically be reminded for pulls',
                value='autoremind',
                emoji=_switch(self.gacha_user.config_data['autoremind']),
                description='Placeholder for an explainer',
            ),
            discord.SelectOption(
                label='Custom remind message',
                value='custom_remind_message',
                emoji=_switch(bool(self.gacha_user.config_data['custom_remind_message'])),
                description='The contents of the pull remind DM',
            ),
            discord.SelectOption(
                label='Custom pull reaction',
                value='custom_pull_reaction',
                emoji=_switch(self.gacha_user.config_data['custom_pull_reaction']),
                description='The reaction when autoremind is ON',
            ),
        ))
        self.primary_select.options = options

    @discord.ui.select(
        placeholder='Select an argument to add',
    )
    async def primary_select(self, interaction: discord.Interaction[Elysia], select: discord.ui.Select[Self]) -> None:
        match select.values[0]:
            case 'cancel_reminder':
                await self.ctx.bot.timer_manager.cancel_timer(
                    user=interaction.user,
                    reserved_type=ReservedTimerType.ANICORD_GACHA,
                )
                self.gacha_user.timer = None
                self.update_display()
                await interaction.response.edit_message(embed=self.embed(), view=self)
                return

            case 'autoremind':
                data = await self.ctx.bot.pool.fetchrow(
                    """
                    UPDATE GachaData
                    SET
                        autoremind = $1
                    WHERE
                        user_id = $2
                    RETURNING
                        *
                    """,
                    not self.gacha_user.config_data['autoremind'],
                    interaction.user.id,
                )
                if data:
                    self.gacha_user = GachaUser(self.user, timer=self.gacha_user.timer, config_data=data)
                self.update_display()
                await interaction.response.edit_message(embed=self.embed(), view=self)
                return

            case 'custom_remind_message':
                await interaction.response.send_modal(
                    GachaCustomInput(
                        self.gacha_user,
                        self,
                        title='Enter message',
                    ),
                )
                return
            case _:
                await interaction.response.send_message('Coming soon!', ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction[Elysia]) -> bool:
        if interaction.user and interaction.user.id == self.user.id:
            return True
        await interaction.response.send_message('This is not for you', ephemeral=True)
        return False


class GachaCustomInput(discord.ui.Modal):
    gacha_input: discord.ui.TextInput[GachaPullView] = discord.ui.TextInput(
        label='Enter custom remind message',
        style=discord.TextStyle.long,
        placeholder='Write $CLEAR to remove it',
        required=True,
        max_length=500,
    )

    def __init__(self, gacha_user: GachaUser, view: GachaPullView, *, title: str) -> None:
        self.gacha_user = gacha_user
        self.view = view
        self.value: str | None = None
        super().__init__(title=title)

    async def on_submit(self, interaction: discord.Interaction[Elysia]) -> None:
        value = self.gacha_input.value

        if value == '$CLEAR':
            value = None

        user_config = await self.view.ctx.bot.pool.fetchrow(
            """
            UPDATE GachaData
            SET
                custom_remind_message = $1
            WHERE
                user_id = $2
            RETURNING
                *
                """,
            value,
            self.gacha_user.user.id,
        )

        if not user_config:
            return

        self.view.gacha_user = GachaUser(
            self.gacha_user.user,
            timer=self.gacha_user.timer,
            config_data=user_config,
        )
        self.view.update_display()

        await interaction.response.edit_message(embed=self.view.embed(), view=self.view)


class GachaPersonalCardsSorter(menus.ListPageSource):
    def __init__(
        self,
        bot: Elysia,
        entries: list[PulledCard],
        *,
        sort_type: int,
        user: discord.User | discord.Member,
    ) -> None:
        self.bot = bot
        self.sort_type = sort_type
        self.user = user

        entries_sorted = list(enumerate(self.sort_cards(entries)))
        super().__init__(entries_sorted, per_page=10)

    async def format_page(
        self,
        _: Paginator,
        entry: list[tuple[int, list[tuple[str, int]] | list[tuple[tuple[int, str, int], int]]]],
    ) -> Embed:
        embed = Embed(
            title='Most pulled cards',
            description='These are your most pulled cards sorted according to what is selected',
            colour=self.user.color,
        )

        embed.set_thumbnail(url=self.user.display_avatar.url)

        match self.sort_type:
            case 2:
                embed.add_field(
                    name='Sorted by character',
                    value='\n'.join([f'{i[0] + 1}. **{i[1][0]}** \n  - Pulled `{i[1][1]}` times' for i in entry]),
                )
            case _:
                embed.add_field(
                    name='Sorted on per card basis',
                    value='\n'.join([
                        (
                            f'{i[0] + 1}. {RARITY_EMOJIS[int(i[1][0][2])]} **{i[1][0][0]} ({i[1][0][1]})**\n'  # pyright: ignore[reportArgumentType, reportGeneralTypeIssues]
                            f'  - Pulled `{i[1][1]}` times'
                        )
                        for i in entry
                    ]),
                )

        return embed

    def sort_cards(self, entries: list[PulledCard]) -> list[tuple[str, int]] | list[tuple[tuple[int, str, int], int]]:
        match self.sort_type:
            case 2:
                c2: dict[str, int] = {}

                for card in entries:
                    c2[card.name or 'Misc'] = c2.get(card.name or 'Misc', 0) + 1

                return sorted(c2.items(), key=operator.itemgetter(1), reverse=True)
            case _:  # Also handles 1
                c1: dict[tuple[int, str, int], int] = {}

                for card in entries:
                    c1[card.id, card.name, card.rarity] = c1.get((card.id, card.name, card.rarity), 0) + 1

                return sorted(c1.items(), key=operator.itemgetter(1), reverse=True)


class GachaStatisticsView(BaseView):
    current: list[PulledCard]
    query: datetime.timedelta | tuple[datetime.datetime | None, datetime.datetime | None] | None

    sort_type: int | None

    ctx: ElyContext

    def __init__(
        self,
        pulls: list[PulledCard],
        user: discord.User | discord.Member,
    ) -> None:
        self.pulls = pulls
        self.user = user
        self.query = None
        self.sort_type = None
        super().__init__()
        self.clear_items()
        self.add_item(self.view_select)

    @classmethod
    async def start(
        cls,
        ctx: ElyContext,
        *,
        pulls: list[PulledCard],
        user: discord.User | discord.Member,
    ) -> None:
        c = cls(pulls, user)
        c.ctx = ctx
        c.current = pulls

        embed = c.embed()

        c.message = await ctx.reply(embed=embed, view=c)

    def embed(self) -> Embed:
        burn_worths = get_burn_worths(self.current)

        embed = Embed(title=f'Pulled cards statistics for {self.user}', colour=self.user.color)
        embed.set_thumbnail(url=self.user.display_avatar.url)

        p_s: list[str] = []
        for k, v in burn_worths.items():
            p_s.append(f'`{k}` {RARITY_EMOJIS[k]} `[{int(v / (5 * k if k != 6 else 1000))}]`: `{v}` blombos')

        p_s.append(f'> Total `[{len(self.current)}]`: `{sum(burn_worths.values())}` blombos')

        embed.add_field(
            value=fmt_str(p_s, seperator='\n'),
        )

        if (first_sync_time := self._get_first_pull(self.pulls)) and first_sync_time and first_sync_time.message_id:
            messages: list[int] = []
            for p in self.pulls:
                if p.message_id and p.message_id not in messages and (p.source and p.source == PullSource.PULLALL.value):  # pyright: ignore[reportUnnecessaryComparison]
                    messages.append(p.message_id)

            times_pulled = len(messages)

            days = (
                datetime.datetime.now(tz=datetime.UTC) - discord.utils.snowflake_time(first_sync_time.message_id)
            ).total_seconds() / 86400

            rate = times_pulled / days
            if days <= 1:
                rate = times_pulled

            embed.add_field(
                value=fmt_str(
                    (
                        '- **Syncing Since:** '
                        + timestamp_str(
                            discord.utils.snowflake_time(first_sync_time.message_id),
                            with_time=True,
                        ),
                        f'  - **Rate :** {rate:.2f} pullall(s) per day',
                        f'  - **Total :** {times_pulled} pullall(s)',
                    ),
                    seperator='\n',
                ),
            )

        return embed

    def _get_first_pull(self, pulls: list[PulledCard]) -> PulledCard | None:
        return next(
            (
                _
                for _ in sorted(
                    (_ for _ in pulls),
                    key=lambda p: discord.utils.snowflake_time(p.message_id).timestamp() if p.message_id else 0,
                )
                if _.message_id
            ),
            None,
        )

    @discord.ui.select(
        placeholder='Select a view',
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label='View total pulls with rarity and pull rate',
                value='1',
                description="See how much you've pulled and how much you've gained along with the rate of pulls per day",
                emoji=RARITY_EMOJIS[1],
            ),
            discord.SelectOption(
                label='View most owned',
                value='2',
                description="See what cards you've pulled multiple times",
                emoji=RARITY_EMOJIS[2],
            ),
        ],
    )
    async def view_select(
        self, interaction: discord.Interaction[Elysia], s: discord.ui.Select[Self]
    ) -> discord.InteractionCallbackResponse[Elysia] | None:
        if s.values:
            match int(s.values[0]):
                case 1:
                    return await interaction.response.edit_message(embed=self.embed(), view=self)
                case 2:
                    await interaction.response.defer()

                    self.sort_type = 1

                    v = Paginator(
                        GachaPersonalCardsSorter(
                            interaction.client,
                            self.current,
                            sort_type=self.sort_type,
                            user=self.user,
                        ),
                        ctx=self.ctx,
                    )

                    v.add_item(self.sort_select)

                    v.add_item(s)

                    await v.start(message=self.message)

                case _:
                    pass
        return None

    @discord.ui.select(
        placeholder='Sort by',
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label='Card',
                value='1',
                emoji=RARITY_EMOJIS[1],
            ),
            discord.SelectOption(
                label='Character',
                value='2',
                emoji=RARITY_EMOJIS[2],
            ),
        ],
    )
    async def sort_select(self, interaction: discord.Interaction[Elysia], s: discord.ui.Select[Self]) -> None:
        self.sort_type = int(s.values[0])
        await interaction.response.defer()

        v = Paginator(
            GachaPersonalCardsSorter(
                interaction.client,
                self.current,
                sort_type=self.sort_type,
                user=self.user,
            ),
            ctx=self.ctx,
        )

        v.add_item(s)

        v.add_item(self.view_select)

        await v.start(message=self.message)
