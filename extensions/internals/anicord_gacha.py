from __future__ import annotations

import asyncio
import datetime
import re
from typing import TYPE_CHECKING, Self

import asyncpg
import discord
from discord import app_commands

from utils import BaseCog, BaseView
from utils.embed import Embed
from utils.helper_functions import better_string, generate_timestamp_string
from utils.subclass import Mafuyu

if TYPE_CHECKING:
    from asyncpg import Record

    from utils import Mafuyu

ANICORD_DISCORD_BOT = 1257717266355851384


class GachaReminderView(BaseView):
    def __init__(
        self,
        cog: AniCordGacha,
        user: discord.User | discord.Member,
        pull_message: discord.Message,
        record: Record | None,
    ) -> None:
        super().__init__()
        self.cog = cog
        self.user = user
        self.pull_message = pull_message
        self.record = record

    @classmethod
    async def start(
        cls,
        cog: AniCordGacha,
        *,
        interaction: discord.Interaction[Mafuyu],
        user: discord.User | discord.Member,
        pull_message: discord.Message,
    ) -> discord.InteractionCallbackResponse[Mafuyu]:
        if pull_message.author.id != ANICORD_DISCORD_BOT:
            return await interaction.response.send_message(
                f'This message is not from the <@{ANICORD_DISCORD_BOT}>.', ephemeral=True
            )

        if not pull_message.embeds:
            return await interaction.response.send_message('This message.... does not have an embed.', ephemeral=True)

        embed = pull_message.embeds[0]

        if not embed.title or not embed.description or embed.title.lower() != 'cards pulled':
            return await interaction.response.send_message('This message is not the pullall message', ephemeral=True)

        if not cls._check_pullall_author(user.id, embed.description):
            return await interaction.response.send_message('This is not your pullall message.', ephemeral=True)

        # The criteria which confirms that this message is the pullall message has
        # been fullfilled is the command executor's has been fullfilled

        record = await cls.fetch_record(interaction.client, user)

        v = cls(cog, user, pull_message, record)

        if record and record['repeating'] is True:
            await v.cog.handle_reminder(v.user, v.pull_message, v.record)
            v.record = await v.fetch_record(interaction.client, v.user)

        embed = v.embed(pull_message)
        return await interaction.response.send_message(embed=embed, view=v, ephemeral=True)

    def embed(self, pull_message: discord.Message) -> Embed:
        next_pull = pull_message.created_at + datetime.timedelta(hours=6)
        return Embed(
            title='Anicord Gacha Helper (Work in progress, may fuck up)',
            description=better_string(
                (
                    f'- **Next Pull in :** {generate_timestamp_string(next_pull)}',
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

    @classmethod
    async def fetch_record(cls, bot: Mafuyu, user: discord.User | discord.Member) -> Record | None:
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

    @classmethod
    def _check_pullall_author(cls, author_id: int, embed_description: str) -> bool:
        lines = embed_description.split('\n')

        author_line = lines[0]

        author_id_parsed = re.findall(r'<@!?([0-9]+)>', author_line)
        if not author_id_parsed:
            return False
        return int(author_id_parsed[0]) == author_id

    @discord.ui.button(label='Remind me')
    async def remind_me_button(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        # Bad implementation incoming
        await self.cog.handle_reminder(self.user, self.pull_message, self.record)
        self.record = await self.fetch_record(interaction.client, interaction.user)
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

    async def get_pull_timer(self) -> Record | None:
        query = """
            SELECT * FROM GachaPullReminders
            WHERE expires < (CURRENT_TIMESTAMP + $1::interval)
            ORDER BY expires
            LIMIT 1;
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
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_punishment_removal())

    async def call_reminder(self, record: Record) -> None:
        user = await self.bot.fetch_user(record['user_id'])
        await user.send('Hey! Pull ')
        await self.bot.pool.execute("""UPDATE GachaPullReminders SET expires = NULL""")  # Reminded.

    async def handle_reminder(
        self,
        user: discord.User | discord.Member,
        pull_messsage: discord.Message,
        record: Record | None,
    ) -> None:
        new_time = pull_messsage.created_at + datetime.timedelta(hours=6)
        if record:
            # We have an existing entry!
            record = await self.bot.pool.fetchrow(
                """UPDATE GachaPullReminders SET expires = $1 WHERE user_id = $2 RETURNING *""",
                new_time,
                user.id,
            )
        else:
            record = await self.bot.pool.fetchrow(
                """INSERT INTO GachaPullReminders VALUES ($1, $2, $3)""",
                user.id,
                False,
                new_time,
            )

        now = datetime.datetime.now(tz=datetime.UTC)
        dur = new_time - now

        if dur.total_seconds() <= (86400 * 40):  # 40 days
            self._have_data.set()

        if self._current_timer and new_time < self._current_timer:
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
