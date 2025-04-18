from __future__ import annotations

import contextlib
import datetime
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

import discord
from discord import app_commands
from discord.ext import commands

from utilities.bases.cog import MafuCog
from utilities.bases.context import MafuContext
from utilities.embed import Embed
from utilities.functions import fmt_str, timestamp_str
from utilities.timers import ReservedTimerType, Timer
from utilities.view import BaseView

if TYPE_CHECKING:
    from asyncpg import Pool, Record

    from utilities.bases.bot import Mafuyu

ANICORD_DISCORD_BOT = 1257717266355851384

PULL_INTERVAL = datetime.timedelta(hours=6)


PULL_LINE_REGEX = r'Name: `(?P<name>.+)` Rarity: <:(?P<rarity>[a-zA-Z0-9]+):.+>.+ ID: `(?P<id>[0-9]+)`'


RARITY_EMOJIS = {
    1: discord.PartialEmoji(id=1259718293410021446, name='RedStar'),
    2: discord.PartialEmoji(id=1259690032554577930, name='GreenStar'),
    3: discord.PartialEmoji(id=1259557039441711149, name='YellowStar'),
    4: discord.PartialEmoji(id=1259718164862996573, name='PurpleStar'),
    5: discord.PartialEmoji(id=1259557105220976772, name='RainbowStar'),
    6: discord.PartialEmoji(id=1259689874961862688, name='BlackStar'),
}


HOLLOW_STAR = discord.PartialEmoji(name='HollowStar', id=1259556949867888660)


def get_burn_worths(pulls: list[PulledCard]) -> dict[int, int]:
    burn_worth: dict[int, int] = {}
    for c in pulls:
        c_burn_worth = c.rarity * 5
        burn_worth[c.rarity] = burn_worth.get(c.rarity, 0) + c_burn_worth
    return {k: burn_worth[k] for k in sorted(burn_worth)}


class GachaUser:
    def __init__(self, user: discord.User | discord.Member, *, timer: Timer | None, config_data: Record) -> None:
        self.user = user
        self.timer = timer
        self.config_data = config_data
        super().__init__()

    @classmethod
    async def from_fetched_record(
        cls,
        pool: Pool[Record],
        *,
        user: discord.User | discord.Member,
    ) -> Self:
        timer = await Timer.from_fetched_record(
            pool,
            user=user,
            reserved_type=ReservedTimerType.ANICORD_GACHA,
        )

        record = await pool.fetchrow(
            """
            INSERT INTO
                GachaData (user_id)
            VALUES
                ($1)
            ON CONFLICT (user_id) DO
            UPDATE
            SET
                user_id = GachaData.user_id
            RETURNING
                *
            """,
            user.id,
        )
        assert record is not None

        return cls(user, timer=timer, config_data=record)

    async def add_card(
        self,
        pool: Pool[Record],
        *,
        card: PulledCard,
        pull_message: discord.Message,
    ) -> None:
        query = """
            INSERT INTO
                GachaPulledCards (user_id, message_id, card_id, card_name, rarity)
            VALUES
                ($1, $2, $3, $4, $5);
            """
        args = (
            self.user.id,
            pull_message.id,
            card.id,
            card.name,
            card.rarity,
        )
        await pool.execute(query, *args)


@dataclass
class PulledCard:
    id: int
    name: str | None
    rarity: int
    message_id: int | None = None

    @classmethod
    def parse_from_str(cls, s: str, /) -> None | Self:
        parsed = re.finditer(PULL_LINE_REGEX, s)

        if not parsed:
            return None

        for _ in parsed:
            d = _.groupdict()

            c_id = int(d['id'])
            rarity = next(k for k, _ in RARITY_EMOJIS.items() if _.name == d['rarity'])
            name: str = d['name']

            return cls(c_id, name, rarity)

        return None


class GachaPullView(BaseView):
    def __init__(
        self,
        ctx: MafuContext,
        user: discord.User | discord.Member,
        pull_message: discord.Message | None,
        gacha_user: GachaUser,
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.user = user
        self.pull_message = pull_message
        self.gacha_user = gacha_user

        self.__pulls_synced: bool = False
        self.__pulls: list[PulledCard] = []

        self._update_display()

    @classmethod
    async def start(
        cls,
        ctx: MafuContext,
        *,
        user: discord.User | discord.Member,
        pull_message: discord.Message | None,
    ) -> discord.InteractionCallbackResponse[Mafuyu] | discord.Message | None:
        gacha_user = await GachaUser.from_fetched_record(ctx.bot.pool, user=user)

        c = cls(ctx, user, pull_message, gacha_user)

        if c.pull_message:
            is_message_syncronised: bool = bool(
                await ctx.bot.pool.fetchval(
                    """
                SELECT
                    EXISTS (
                        SELECT
                            *
                        FROM
                            GachaPulledCards
                        WHERE
                            user_id = $1
                            AND message_id = $2
                    );
                """,
                    user.id,
                    c.pull_message.id,
                )
            )

            c.__pulls_synced = is_message_syncronised
            c._update_display()

        embed = c.embed()

        return await ctx.reply(embed=embed, view=c, ephemeral=False)

    def embed(self) -> Embed:
        embed = Embed(title='Anicord Gacha Bot Helper')

        s: list[str] = []

        if self.gacha_user.timer is None:
            s.append('- You do not have a pull reminder setup yet.')

        now = datetime.datetime.now(tz=datetime.UTC)

        next_pull = (
            self.gacha_user.timer.expires
            if self.gacha_user.timer  # If we have a pull timer already, use that
            else self.pull_message.created_at + PULL_INTERVAL
            if self.pull_message and self.pull_message.created_at + PULL_INTERVAL >= now
            else None
        )

        if next_pull:
            s.append(f'> **Next Pull in :** {timestamp_str(next_pull, with_time=True)}')
            if self.gacha_user.timer:
                s.append('-# You will be reminded in DMs when you can pull again.')

        if self.__pulls:
            burn_worth = get_burn_worths(self.__pulls)

            p_s: list[str] = []
            for k, v in burn_worth.items():
                p_s.append(f'`{k}` {RARITY_EMOJIS[k]} `[{int(v / (5 * k))}]`: `{v}` blombos')

            p_s.append(f'> Total: `{sum(burn_worth.values())}` blombos')

            embed.add_field(
                name='Estimated burn worth:',
                value=fmt_str(p_s, seperator='\n'),
            )

        embed.description = fmt_str(s, seperator='\n')

        return embed

    def _update_display(self) -> None:
        self.clear_items()

        is_timer = self.gacha_user.timer is not None

        if self.pull_message:
            self.add_item(self.remind_me_button)

            if self.__pulls_synced is False:
                self.add_item(self.sync_pulls)

        elif self.pull_message is None and is_timer:
            self.add_item(self.remind_me_button)

        self.remind_me_button.style = discord.ButtonStyle.red if is_timer else discord.ButtonStyle.green
        self.remind_me_button.label = 'Cancel reminder' if is_timer else 'Remind me'

    @discord.ui.button(emoji='\U000023f0', label='Remind me', style=discord.ButtonStyle.gray)
    async def remind_me_button(
        self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]
    ) -> None | discord.InteractionCallbackResponse[Mafuyu]:
        # Bad implementation incoming

        if self.gacha_user.timer:
            await self.ctx.bot.timer_manager.cancel_timer(
                user=interaction.user,
                reserved_type=ReservedTimerType.ANICORD_GACHA,
            )
            self.gacha_user.timer = None  # Timer gone.
            self._update_display()

            return await interaction.response.edit_message(
                content='Successfully removed pull reminder',
                embed=self.embed(),
                view=self,
            )

        if not self.pull_message:
            # Never will occur
            await interaction.response.defer()
            return None

        remind_time = self.pull_message.created_at + PULL_INTERVAL

        self.gacha_user.timer = await self.ctx.bot.timer_manager.create_timer(
            remind_time,
            user=interaction.user,
            reserved_type=ReservedTimerType.ANICORD_GACHA,
        )
        self._update_display()

        return await interaction.response.edit_message(
            content='Successfully created a pull reminder',
            embed=self.embed(),
            view=self,
        )

    @discord.ui.button(emoji='\U0001f4e5', label='Syncronize pulls', style=discord.ButtonStyle.grey)
    async def sync_pulls(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        assert self.pull_message is not None

        embed = self.pull_message.embeds[0]

        assert embed.description is not None

        pulls = [_ for _ in (PulledCard.parse_from_str(_) for _ in embed.description.split('\n')) if _ is not None]

        for card in pulls:
            await self.gacha_user.add_card(
                self.ctx.bot.pool,
                card=card,
                pull_message=self.pull_message,
            )
            self.__pulls.append(card)

        self.__pulls_synced = True
        self._update_display()

        await interaction.response.edit_message(
            content=f'Your {len(pulls)} cards have been added to tracking database',
            embed=self.embed(),
            view=self,
        )
    async def interaction_check(self, interaction: discord.Interaction[Mafuyu]):
        if interaction.user and interaction.user.id == self.user.id:
            return True
        await interaction.response.send_message('This is not for you', ephemeral=True)
        return False

class AniCordGacha(MafuCog):
    def __init__(self, bot: Mafuyu) -> None:
        super().__init__(bot)

        self.ctx_menu = app_commands.ContextMenu(
            name='Pullall Message Helper',
            callback=self.pull_message_menu,
        )

        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.Cog.listener('on_timer_expire')
    async def pull_timer_expire(self, timer: Timer) -> None:
        if timer.reserved_type != ReservedTimerType.ANICORD_GACHA:
            return
        with contextlib.suppress(discord.HTTPException):
            user = await self.bot.fetch_user(timer.user_id)
            await user.send("Hey! It's been 6 hours since you last pulled. You should pull again")

    def _check_pullall_author(self, author_id: int, embed_description: str) -> bool:
        lines = embed_description.split('\n')

        author_line = lines[0]

        author_id_parsed = re.findall(r'<@!?([0-9]+)>', author_line)

        if not author_id_parsed:
            return False

        return int(author_id_parsed[0]) == author_id

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def pull_message_menu(
        self,
        interaction: discord.Interaction[Mafuyu],
        message: discord.Message,
    ) -> discord.InteractionCallbackResponse[Mafuyu] | None:
        # Few checks

        m = None

        if message.author.id != ANICORD_DISCORD_BOT:
            m = f'This message is not from the <@{ANICORD_DISCORD_BOT}>.'

        elif not message.embeds:
            m = 'This message.... does not have an embed.'

        elif (embed := message.embeds[0]):
            if (not embed.title or not embed.description or embed.title.lower() != 'cards pulled'):
                m = 'This message is not the pullall message'
            elif not self._check_pullall_author(
                interaction.user.id,
                embed.description,
            ):
                m = 'This is not your pullall message.'

        if m:
            return await interaction.response.send_message(m, ephemeral=True)

        # These are a lot of checks to avoid yk using the wrong data.
        # The messages are reduces to an amount which isnt much
        # but is enough to convey most of the information required

        await GachaPullView.start(
            await MafuContext.from_interaction(interaction),
            user=interaction.user,
            pull_message=message,
        )
        return None

    @commands.hybrid_group(name='gacha', description='Handles Anicord Gacha Bot', fallback='status')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def gacha_group(self, ctx: MafuContext) -> None:
        await GachaPullView.start(ctx, user=ctx.author, pull_message=None)

    @gacha_group.command(
        name='statistics',
        description='Given you have syncronized pulls at least ones, this command provides statistics for it.',
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def gacha_statistics(
        self,
        ctx: MafuContext,
        user: discord.User | discord.Member = commands.Author,
    ) -> None:
        pull_records = await self.bot.pool.fetch(
            """
            SELECT
                message_id,
                card_id,
                card_name,
                rarity
            FROM
                GachaPulledCards
            WHERE
                user_id = $1
            """,
            user.id,
        )
        if not pull_records:
            raise commands.BadArgument(
                'You never syncronised your pulls. You bitch. Why would you run random commands. Smh.'
            )

        pulls = [
            PulledCard(
                p['card_id'],
                p['card_name'],
                p['rarity'],
                p['message_id'],
            )
            for p in pull_records
        ]
        burn_worths = get_burn_worths(pulls)
        embed = Embed(title=f'Pulled cards statistics for {user}')
        embed.set_thumbnail(url=user.display_avatar.url)

        p_s: list[str] = []
        for k, v in burn_worths.items():
            p_s.append(f'`{k}` {RARITY_EMOJIS[k]} `[{int(v / (5 * k))}]`: `{v}` blombos')

        p_s.append(f'> Total `[{len(pulls)}]`: `{sum(burn_worths.values())}` blombos')

        embed.add_field(
            value=fmt_str(p_s, seperator='\n'),
        )

        first_sync_time = next(
            (
                _.message_id
                for _ in sorted(
                    (_ for _ in pulls),
                    key=lambda p: discord.utils.snowflake_time(p.message_id).timestamp() if p.message_id else 0,
                )
                if _.message_id
            ),
            None,
        )

        if first_sync_time:
            messages: list[int] = []
            for p in pulls:
                if p.message_id and p.message_id not in messages:
                    messages.append(p.message_id)

            times_pulled = len(messages)

            days = (
                datetime.datetime.now(tz=datetime.UTC) - discord.utils.snowflake_time(first_sync_time)
            ).total_seconds() / 86400

            rate = times_pulled / days
            if days <= 1:
                rate = times_pulled

            embed.add_field(
                value=fmt_str(
                    (
                        '- **Syncing Since:** '
                        + timestamp_str(
                            discord.utils.snowflake_time(first_sync_time),
                            with_time=True,
                        ),
                        f'  - **Rate :** {rate:.2f} pullall(s) per day',
                        f'  - **Total :** {times_pulled} pullall(s)',
                    ),
                    seperator='\n',
                ),
            )

        await ctx.reply(embed=embed)
