from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from extensions.tracksy.constants import ANICORD_GACHA_SERVER, RARITY_EMOJIS
from extensions.tracksy.types import Card, PullType
from utilities.bases.cog import CyCog
from utilities.embed import Embed
from utilities.functions import fmt_str, timestamp_str
from utilities.view import BaseView

if TYPE_CHECKING:
    from utilities.bases.context import CyContext


def get_burn_worths(pulls: list[Card]) -> dict[int, int]:
    burn_worth: dict[int, int] = {}
    for c in pulls:
        c_burn_worth = 1 if c.rarity == 7 else (c.rarity * 5 if c.rarity != 6 else 1000)
        burn_worth[c.rarity] = burn_worth.get(c.rarity, 0) + c_burn_worth
    return {k: burn_worth[k] for k in sorted(burn_worth)}


class GachaStatisticsView(BaseView):
    ctx: CyContext

    def __init__(self, pulls: list[Card], user: discord.User | discord.Member) -> None:
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
        pulls: list[Card],
        user: discord.User | discord.Member,
    ) -> None:
        c = cls(pulls, user)
        c.ctx = ctx

        embed = c.embed()

        c.message = await ctx.reply(embed=embed, view=c)

    def embed(self) -> Embed:
        burn_worths = get_burn_worths(self.pulls)

        embed = Embed(
            title=f'Pulled cards statistics for {self.user}',
            colour=self.user.color if self.ctx.guild and self.ctx.guild.id == ANICORD_GACHA_SERVER else None,
        )
        embed.set_thumbnail(url=self.user.display_avatar.url)

        p_s: list[str] = []
        for k, v in burn_worths.items():
            p_s.append(f'`{k}` {RARITY_EMOJIS[k]} `[{int(v / (1 if k == 7 else (5 * k if k != 6 else 1000)))}]`: `{v}` blombos')

        p_s.append(f'> Total `[{len(self.pulls)}]`: `{sum(burn_worths.values())}` blombos')

        embed.add_field(
            value=fmt_str(p_s, seperator='\n'),
        )

        messages: list[int] = []

        pullalls = [p for p in self.pulls if p.source == PullType.PULLALL]

        if (first_sync_time := self._get_first_pull(pullalls)) and first_sync_time and first_sync_time.message:
            messages = []
            for p in pullalls:
                if p.message and p.message not in messages and (p.source and p.source == PullType.PULLALL):
                    messages.append(p.message)

            times_pulled = len(messages)

            days = (
                datetime.datetime.now(tz=datetime.UTC) - discord.utils.snowflake_time(first_sync_time.message)
            ).total_seconds() / 86400

            rate = times_pulled / days
            if days <= 1:
                rate = times_pulled

            embed.add_field(
                name='Stats for pullall',
                value=fmt_str(
                    (
                        '- **Syncing Since:** '
                        + timestamp_str(
                            discord.utils.snowflake_time(first_sync_time.message),
                            with_time=True,
                        ),
                        f'  - **Rate :** {rate:.2f} pullall(s) per day',
                        f'  - **Total :** {times_pulled} pullall(s)',
                    ),
                    seperator='\n',
                ),
            )

        pack_pulls = [p for p in self.pulls if p.source == PullType.PACK]

        if (first_sync_time := self._get_first_pull(pack_pulls)) and first_sync_time and first_sync_time.message:
            messages = []
            for p in pack_pulls:
                if p.message and p.message not in messages and (p.source and p.source == PullType.PACK):
                    messages.append(p.message)

            times_pulled = len(messages)

            days = (
                datetime.datetime.now(tz=datetime.UTC) - discord.utils.snowflake_time(first_sync_time.message)
            ).total_seconds() / 86400

            rate = times_pulled / days
            if days <= 1:
                rate = times_pulled

            embed.add_field(
                name='Packs stats',
                value=fmt_str(
                    (
                        '- **Syncing Since:** '
                        + timestamp_str(
                            discord.utils.snowflake_time(first_sync_time.message),
                            with_time=True,
                        ),
                        f'  - **Rate :** {rate:.2f} packs(s) per day',
                        f'  - **Total :** {times_pulled} packs(s)',
                    ),
                    seperator='\n',
                ),
            )

        embed.set_footer(text='This ui sucks ass')

        return embed

    def _get_first_pull(self, pulls: list[Card]) -> Card | None:
        return next(
            (
                _
                for _ in sorted(
                    (_ for _ in pulls),
                    key=lambda p: discord.utils.snowflake_time(p.message).timestamp() if p.message else 0,
                )
                if _.message
            ),
            None,
        )


class Frontend(CyCog):
    @commands.hybrid_command(
        name='statistics',
        description='Given you have syncronized pulls at least ones, this command provides statistics for it.',
        aliases=['stats', 'stat'],
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def gacha_statistics(
        self,
        ctx: CyContext,
        user: discord.User | discord.Member = commands.Author,
    ) -> None:
        pull_records = await self.bot.pool.fetch(
            """
            SELECT
                channel_id,
                message_id,
                user_id,
                card_id,
                card_name,
                rarity,
                pull_source
            FROM
                GachaPulledCards
            WHERE
                user_id = $1
            """,
            user.id,
        )
        if not pull_records:
            raise commands.BadArgument("You don't have any pulls syncronised with me.")

        pulls = [
            Card(
                self.bot.get_channel(p['channel_id']),  # pyright: ignore[reportArgumentType]
                p['message_id'],
                user,
                p['card_id'],
                p['card_name'],
                p['rarity'],
                p['pull_source'],
            )
            for p in pull_records
        ]

        await GachaStatisticsView.start(ctx, pulls=pulls, user=user)
