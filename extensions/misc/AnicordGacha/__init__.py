from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from extensions.misc.AnicordGacha.bases import PulledCard
from extensions.misc.AnicordGacha.constants import ANICORD_DISCORD_BOT
from extensions.misc.AnicordGacha.utils import check_pullall_author
from extensions.misc.AnicordGacha.views import GachaPullView, GachaStatisticsView
from utilities.bases.cog import MafuCog
from utilities.bases.context import MafuContext
from utilities.timers import ReservedTimerType, Timer

if TYPE_CHECKING:
    from utilities.bases.bot import Mafuyu


class AniCordGacha(MafuCog):
    def __init__(self, bot: Mafuyu) -> None:
        super().__init__(bot)

        self.ctx_menu = app_commands.ContextMenu(
            name='Pulls syncronise and remind',
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

        elif embed := message.embeds[0]:
            if not embed.title or not embed.description or embed.title.lower() != 'cards pulled':
                m = 'This message is not the pullall message'
            elif not check_pullall_author(
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
            raise commands.BadArgument("You don't have any pulls syncronised with me.")

        pulls = [
            PulledCard(
                p['card_id'],
                p['card_name'],
                p['rarity'],
                p['message_id'],
            )
            for p in pull_records
        ]

        await GachaStatisticsView.start(ctx, pulls=pulls, user=user)
