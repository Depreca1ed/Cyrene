from __future__ import annotations

import asyncio
import contextlib
import datetime
import re
from typing import TYPE_CHECKING, Self

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, BaseView
from utils.embed import Embed
from utils.helper_functions import better_string, generate_timestamp_string

if TYPE_CHECKING:
    from asyncpg import Record

    from utils import Mafuyu
    from utils.subclass import Context

ANICORD_DISCORD_BOT = 1257717266355851384


async def fetch_record(bot: Mafuyu, user: discord.User | discord.Member) -> Record | None:
    return await bot.pool.fetchrow(
        """
            SELECT
                user_id,
                repeating,
                expires
            from
                GachaPullReminders
            WHERE
                user_id = $1;
            """,
        user.id,
    )


async def remove_reminder(bot: Mafuyu, record: Record) -> None:
    await bot.pool.execute(
        """
            UPDATE GachaPullReminders
            SET
                expires = NULL
            WHERE
                user_id = $1;
            """,
        record['user_id'],
    )


def check_pullall_author(author_id: int, embed_description: str) -> bool:
    lines = embed_description.split('\n')

    author_line = lines[0]

    author_id_parsed = re.findall(r'<@!?([0-9]+)>', author_line)

    if not author_id_parsed:
        return False

    return int(author_id_parsed[0]) == author_id


class GachaReminderView(BaseView):
    def __init__(
        self,
        cog: AniCordGacha,
        user: discord.User | discord.Member,
        pull_message: discord.Message | None,
        record: Record | None,
    ) -> None:
        super().__init__()
        self.cog = cog
        self.user = user
        self.pull_message = pull_message
        self.record = record
        self.clear_items()

        if self.pull_message:
            self._update_display()
            self.add_item(self.remind_me_button)

    @classmethod
    async def start(
        cls,
        cog: AniCordGacha,
        *,
        interaction: discord.Interaction[Mafuyu] | Context,
        user: discord.User | discord.Member,
        pull_message: discord.Message | None,
    ) -> discord.InteractionCallbackResponse[Mafuyu] | discord.Message:
        bot = interaction.client if isinstance(interaction, discord.Interaction) else interaction.bot
        send = interaction.response.send_message if isinstance(interaction, discord.Interaction) else interaction.send

        if pull_message:
            if pull_message.author.id != ANICORD_DISCORD_BOT:
                return await send(f'This message is not from the <@{ANICORD_DISCORD_BOT}>.', ephemeral=True)

            if not pull_message.embeds:
                return await send('This message.... does not have an embed.', ephemeral=True)

            embed = pull_message.embeds[0]

            if not embed.title or not embed.description or embed.title.lower() != 'cards pulled':
                return await send('This message is not the pullall message', ephemeral=True)

            if not check_pullall_author(user.id, embed.description):
                return await send('This is not your pullall message.', ephemeral=True)

        # The criteria which confirms that this message is the pullall message has
        # been fullfilled is the command executor's has been fullfilled

        record = await fetch_record(
            bot,
            user,
        )

        v = cls(cog, user, pull_message, record)

        if v.pull_message and record and record['repeating'] is True:
            # Basically automatically setup reminder if they have repeating as True

            await v.cog.handle_reminder(v.user, v.pull_message)
            v.record = await fetch_record(bot, v.user)

        embed = v.embed(pull_message, v.record)

        return await send(embed=embed, view=v, ephemeral=True)

    def embed(self, pull_message: discord.Message | None = None, record: Record | None = None) -> Embed:
        next_pull: datetime.datetime | None = (
            pull_message.created_at + datetime.timedelta(hours=6) if pull_message else record['expires'] if record else None
        )

        return Embed(
            title='Anicord Gacha Helper',
            description=better_string(
                (
                    f'- **Next Pull in :** {generate_timestamp_string(next_pull, with_time=True)}' if next_pull else None,
                    (
                        '> You will be reminded when the pull happens.'
                        '\n-# To not be reminded, click the remind me button again'
                    )
                    if self.record and self.record['expires']
                    else None,
                    '-# You have auto remind enabled' if self.record and self.record['repeating'] is True else None,
                ),
                seperator='\n',
            ),
        )

    def _update_display(self) -> None:
        if self.record:
            self.remind_me_button.style = discord.ButtonStyle.green if self.record['expires'] else discord.ButtonStyle.red

    @discord.ui.button(label='Remind me', style=discord.ButtonStyle.gray)
    async def remind_me_button(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        # Bad implementation incoming
        if not self.pull_message:
            # Never will occur
            await interaction.response.defer()
            return

        if self.record and self.record['expires']:
            await remove_reminder(interaction.client, self.record)

            self.record = await fetch_record(interaction.client, interaction.user)
            self._update_display()
            self.cog.restart_task()

            await interaction.response.edit_message(
                content='I have successfully removed your reminder',
                embed=self.embed(self.pull_message),
            )

        await self.cog.handle_reminder(self.user, self.pull_message)

        self.record = await fetch_record(interaction.client, interaction.user)
        self._update_display()

        await interaction.response.edit_message(
            content='I have successfully setup a reminder',
            embed=self.embed(
                self.pull_message,
            ),
        )


class AniCordGacha(BaseCog):
    def __init__(self, bot: Mafuyu) -> None:
        super().__init__(bot)
        self._current_timer: datetime.datetime | None = (
            None  # This is the timestamp fo the latest punishment to be dispatched
        )
        self._have_data = asyncio.Event()
        self._task = self.bot.loop.create_task(self.dispatch_punishment_removal())

        self.ctx_menu = app_commands.ContextMenu(
            name='Pullall Message Helper',
            callback=self.pull_message_menu,
        )

        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)
        self._task.cancel()

    async def get_pull_timer(self) -> Record | None:
        query = """
                SELECT
                    *
                FROM
                    GachaPullReminders
                WHERE
                    expires < (CURRENT_TIMESTAMP + $1::interval)
                ORDER BY
                    expires
                LIMIT
                    1;
                """

        return await self.bot.pool.fetchrow(query, datetime.timedelta(days=40))

    async def wait_for_active_punishments(self) -> Record:
        p = await self.get_pull_timer()
        if p is not None:
            self._have_data.set()
            return p

        self._have_data.clear()
        self._current_timer = None
        await self._have_data.wait()

        return await self.get_pull_timer()  # pyright: ignore[reportReturnType]

    async def dispatch_punishment_removal(self) -> None:
        try:
            while not self.bot.is_closed():
                p = await self.wait_for_active_punishments()

                self._current_timer = p['expires']
                expire: datetime.datetime = p['expires']

                now = datetime.datetime.now(tz=datetime.UTC)

                if expire >= now:
                    to_sleep = (expire - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_reminder(p)

        except asyncio.CancelledError:
            raise

        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self.restart_task()

    async def call_reminder(self, record: Record) -> None:
        with contextlib.suppress(discord.HTTPException):
            user = await self.bot.fetch_user(record['user_id'])
            await user.send(
                (
                    "Hey! It's been 6 hours since you last pulled. You should pull again.\n"
                    '-# Remember to run the menu thing again. Otherwise, I would know when to remind you again.'
                ),
            )
        await remove_reminder(self.bot, record)

    async def handle_reminder(
        self,
        user: discord.User | discord.Member,
        pull_messsage: discord.Message,
    ) -> None:
        new_time = pull_messsage.created_at + datetime.timedelta(hours=6)
        await self.bot.pool.execute(
            """

            INSERT INTO
                GachaPullReminders
            VALUES
                ($1, $2, $3)
            ON CONFLICT (user_id) DO
            UPDATE
            SET
                expires = $3;
            """,
            user.id,
            False,
            new_time,
        )

        now = datetime.datetime.now(tz=datetime.UTC)
        dur = new_time - now

        if dur.total_seconds() <= (86400 * 40):  # 40 days
            self._have_data.set()

        if self._current_timer and new_time < self._current_timer:
            self.restart_task()

    def restart_task(self) -> None:
        self._task.cancel()
        self._task = self.bot.loop.create_task(self.dispatch_punishment_removal())

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def pull_message_menu(self, interaction: discord.Interaction[Mafuyu], message: discord.Message) -> None:
        await GachaReminderView.start(
            self,
            interaction=interaction,
            user=interaction.user,
            pull_message=message,
        )

    @commands.hybrid_group(name='gacha', description='Handles Anicord Gacha Bot', fallback='status')
    async def gacha_group(self, ctx: Context) -> None:
        await GachaReminderView.start(self, interaction=ctx.interaction or ctx, user=ctx.author, pull_message=None)
