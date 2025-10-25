from __future__ import annotations

import contextlib
import datetime
from typing import TYPE_CHECKING, Self

import discord

from extensions.anicord_gacha.bases import GachaUser, PulledCard
from extensions.anicord_gacha.constants import GACHA_SERVER, RARITY_EMOJIS, PullSource
from extensions.anicord_gacha.utils import get_burn_worths, switch
from utilities.constants import BASE_COLOUR, BotEmojis
from utilities.embed import Embed
from utilities.functions import fmt_str, timestamp_str
from utilities.view import BaseView

if TYPE_CHECKING:
    from utilities.bases.bot import Cyrene
    from utilities.bases.context import CyContext


class GachaPullView(discord.ui.LayoutView):
    message: discord.Message | None

    def __init__(
        self,
        ctx: CyContext,
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
        ctx: CyContext,
        *,
        user: discord.User | discord.Member,
    ) -> discord.InteractionCallbackResponse[Cyrene] | discord.Message | None:
        gacha_user = await GachaUser.from_fetched_record(ctx.bot.pool, user=user)

        c = cls(ctx, user, gacha_user)
        return await ctx.reply(view=c)

    def display(self) -> discord.ui.Container[Self]:
        container = discord.ui.Container(
            accent_color=self.user.color if self.ctx.guild and self.ctx.guild.id == GACHA_SERVER else BASE_COLOUR
        )

        container.add_item(
            discord.ui.Section(
                fmt_str(
                    (
                        '## Gacha helper configuration',
                        f'> **Next Pull :** {timestamp_str(self.gacha_user.timer.expires, with_time=True)}'
                        if self.gacha_user.timer is not None
                        else None,
                    ),
                    seperator='\n',
                ),
                accessory=discord.ui.Thumbnail(BotEmojis.CYRENE1.url),
            )
        )

        container.add_item(
            discord.ui.Section(
                '### Auto pull reminder',
                (
                    '> -# When this option is enabled,'
                    ' you will be notified when you are supposed '
                    'to pull, using the time when you last did a pullall'
                ),
                accessory=AutoRemindButton(is_enabled=self.gacha_user.config_data['autoremind']),
            )
        )

        container.add_item(
            discord.ui.Section(
                '### Reminder message',
                (
                    '> -# You can set what message you want to be sent '
                    'by the bot when it DMs you to remind you that you '
                    'need to pull'
                ),
                accessory=ReminderMessageButton(is_enabled=bool(self.gacha_user.config_data['custom_remind_message'])),
            )
        )

        return container

    def update_display(self) -> None:
        self.clear_items()
        self.add_item(self.display())

    async def interaction_check(self, interaction: discord.Interaction[Cyrene]) -> bool:
        if interaction.user and interaction.user.id == self.user.id:
            return True
        await interaction.response.send_message('This is not for you', ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        with contextlib.suppress(discord.errors.NotFound):
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=None)
        self.stop()


class AutoRemindButton(discord.ui.Button[GachaPullView]):
    view: GachaPullView

    def __init__(self, *, is_enabled: bool) -> None:
        self.is_enabled = is_enabled
        super().__init__(style=discord.ButtonStyle.gray, emoji=switch(self.is_enabled))

    async def callback(self, interaction: discord.Interaction[Cyrene]) -> None:
        data = await self.view.ctx.bot.pool.fetchrow(
            """
            UPDATE GachaData
            SET
                autoremind = $1
            WHERE
                user_id = $2
            RETURNING
                *
            """,
            not self.view.gacha_user.config_data['autoremind'],
            interaction.user.id,
        )
        if data:
            self.view.gacha_user = GachaUser(self.view.user, timer=self.view.gacha_user.timer, config_data=data)
        self.view.update_display()
        await interaction.response.edit_message(view=self.view)


class ReminderMessageButton(discord.ui.Button[GachaPullView]):
    view: GachaPullView

    def __init__(self, *, is_enabled: bool) -> None:
        self.is_enabled = is_enabled
        super().__init__(style=discord.ButtonStyle.gray, emoji=switch(self.is_enabled))

    async def callback(self, interaction: discord.Interaction[Cyrene]) -> None:
        await interaction.response.send_modal(
            GachaCustomInput(
                self.view.gacha_user,
                self.view,
                title='Enter message',
            ),
        )


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

    async def on_submit(self, interaction: discord.Interaction[Cyrene]) -> None:
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

        await interaction.response.edit_message(view=self.view)


class GachaStatisticsView(BaseView):
    current: list[PulledCard]
    query: datetime.timedelta | tuple[datetime.datetime | None, datetime.datetime | None] | None

    sort_type: int | None

    ctx: CyContext

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
        ctx: CyContext,
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

        embed = Embed(
            title=f'Pulled cards statistics for {self.user}',
            colour=self.user.color if self.ctx.guild and self.ctx.guild.id == GACHA_SERVER else None,
        )
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
