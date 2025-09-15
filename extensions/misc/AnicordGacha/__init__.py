from __future__ import annotations

import contextlib
import random
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from extensions.misc.AnicordGacha.bases import GachaUser, PulledCard, PullSource
from extensions.misc.AnicordGacha.constants import ANICORD_DISCORD_BOT, PULL_INTERVAL, RARITY_PULL_MESSAGES
from extensions.misc.AnicordGacha.utils import check_pullall_author as check_pullall_author
from extensions.misc.AnicordGacha.views import GachaPullView, GachaStatisticsView
from utilities.bases.cog import MafuCog
from utilities.functions import fmt_str as fmt_str
from utilities.timers import ReservedTimerType, Timer

if TYPE_CHECKING:
    from utilities.bases.bot import Mafuyu
    from utilities.bases.context import MafuContext


DEFAULT_REMIND_MESSAGE: str = "Hey! It's been 6 hours since you last pulled. You should pull again"


class AniCordGacha(MafuCog):
    def __init__(self, bot: Mafuyu) -> None:
        self.user_cache = {}
        super().__init__(bot)

    @commands.Cog.listener('on_timer_expire')
    async def pull_timer_expire(self, timer: Timer) -> None:
        if timer.reserved_type != ReservedTimerType.ANICORD_GACHA:
            return
        with contextlib.suppress(discord.HTTPException):
            user = await self.bot.fetch_user(timer.user_id)
            gacha_user = await GachaUser.from_fetched_record(self.bot.pool, user=user)

            remind_message = gacha_user.config_data['custom_remind_message'] or DEFAULT_REMIND_MESSAGE

            await user.send(remind_message)

    async def handle_pullall(self, message: discord.Message) -> None:
        embed = message.embeds[0]
        assert embed.description is not None

        pulls = [_ for _ in (PulledCard.parse_from_pullall_str(_) for _ in embed.description.split('\n')) if _ is not None]

        lines = embed.description.split('\n')

        author_line = lines[0]

        author_id_parsed = re.findall(r'<@!?([0-9]+)>', author_line)

        if not author_id_parsed:
            return
        user = self.bot.get_user(author_id_parsed[0]) or self.user_cache.get(author_id_parsed[0])

        if user is None:
            user = await self.bot.fetch_user(author_id_parsed[0])
            self.user_cache[author_id_parsed[0]] = user

        is_message_syncronised: bool = bool(
            await self.bot.pool.fetchval(
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
                message.id,
            )
        )
        if is_message_syncronised is True:
            return

        gacha_user = await GachaUser.from_fetched_record(self.bot.pool, user=user)

        for card in pulls:
            await gacha_user.add_card(
                self.bot.pool,
                card=card,
                pull_message=message,
                source=PullSource.PULLALL,
            )
            if "elysia" in card.name.lower():
                await self.bot.logger.send(f"Elysia (ID:{card.id}) pulled by {str(user)}")

        if gacha_user.config_data['autoremind'] is True:
            new_remind_time = message.created_at + PULL_INTERVAL

            if new_remind_time < discord.utils.utcnow():
                return

            await self.bot.timer_manager.create_timer(
                new_remind_time,
                user=gacha_user.user,
                reserved_type=ReservedTimerType.ANICORD_GACHA,
            )

            with contextlib.suppress(discord.HTTPException):
                await message.add_reaction(random.choice(message.guild.emojis))  # pyright: ignore[reportOptionalMemberAccess]  # noqa: S311

    async def handle_single_pull(self, message: discord.Message) -> None:
        embed = message.embeds[0]
        assert embed.description is not None

        user = message.mentions[0]

        card = PulledCard.parse_from_single_pull(embed)

        if card is None:
            return
        is_message_syncronised: bool = bool(
            await self.bot.pool.fetchval(
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
                message.id,
            )
        )
        if is_message_syncronised is True:
            return

        gacha_user = await GachaUser.from_fetched_record(self.bot.pool, user=user)

        await gacha_user.add_card(
            self.bot.pool,
            card=card,
            pull_message=message,
            source=PullSource.PULL,
        )

    @commands.Cog.listener('on_message')
    async def gacha_message_listener(self, message: discord.Message) -> None:
        if message.author.id != ANICORD_DISCORD_BOT:
            # if message.author.id != self.bot.user.id:
            return None

        if not message.embeds:
            return None

        embed = message.embeds[0]

        if embed.title and embed.description and embed.title.lower() == 'cards pulled':
            return await self.handle_pullall(message)

        if message.content:
            author_id_parsed = re.findall(r'<@!?([0-9]+)>', message.content)

            if message.content in [f'<@{author_id_parsed[0]}> {t}' for t in RARITY_PULL_MESSAGES.values()]:
                return await self.handle_single_pull(message)

        return None

    @commands.hybrid_command(name='gacha', description='Handles Anicord Gacha Bot')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def gacha(self, ctx: MafuContext) -> None:
        await GachaPullView.start(ctx, user=ctx.author)

    @commands.hybrid_command(
        name='statistics',
        description='Given you have syncronized pulls at least ones, this command provides statistics for it.',
        aliases=['stats', 'stat'],
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
            PulledCard(
                p['card_id'],
                p['card_name'],
                p['rarity'],
                p['message_id'],
                source=p['pull_source'],
            )
            for p in pull_records
        ]

        await GachaStatisticsView.start(ctx, pulls=pulls, user=user)

    @commands.hybrid_command(name='nextpull', description='Tells you when you can pull again', aliases=['np'])
    @app_commands.allowed_installs(guilds=True, users=True)
    async def next_pull(self, ctx: MafuContext, *, user: discord.User = commands.Author) -> discord.Message:
        gacha_user = await GachaUser.from_fetched_record(ctx.bot.pool, user=user)

        if gacha_user.config_data['autoremind'] is False:
            return await ctx.reply('You have disabled automatic reminders for pulls.')

        if gacha_user.timer:
            name = 'You' if ctx.author.id == user.id else str(user)
            return await ctx.reply(f'{name} can cook {discord.utils.format_dt(gacha_user.timer.expires, "R")}')
        return await ctx.reply('COOK! NOW!')
