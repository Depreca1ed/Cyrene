from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Self

import discord
import humanize

from extensions.misc.AnicordGacha.bases import GachaUser, PulledCard, PullSource
from extensions.misc.AnicordGacha.constants import RARITY_EMOJIS
from extensions.misc.AnicordGacha.utils import get_burn_worths
from utilities.bases.bot import Elysia
from utilities.constants import BotEmojis
from utilities.embed import Embed
from utilities.functions import fmt_str, timestamp_str
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
