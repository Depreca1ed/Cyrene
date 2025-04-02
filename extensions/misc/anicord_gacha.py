from __future__ import annotations

import contextlib
import datetime
import re
from typing import TYPE_CHECKING, Self

import discord
from discord import app_commands
from discord.ext import commands

from utils import BaseCog, BaseView
from utils.embed import Embed
from utils.helper_functions import better_string, generate_timestamp_string
from utils.subclass import Context, Mafuyu
from utils.timer_manager import ReservedTimerType, Timer

if TYPE_CHECKING:
    import asyncpg
    from discord.ext.commands._types import Check  # pyright: ignore[reportMissingTypeStubs]

    from utils import Mafuyu

ANICORD_DISCORD_BOT = 1257717266355851384

PULL_INTERVAL = datetime.timedelta(hours=6)


def check_pullall_author(author_id: int, embed_description: str) -> bool:
    lines = embed_description.split('\n')

    author_line = lines[0]

    author_id_parsed = re.findall(r'<@!?([0-9]+)>', author_line)

    if not author_id_parsed:
        return False

    return int(author_id_parsed[0]) == author_id


def pullall_check() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        msg = ctx.message

        m = None

        if msg.author.id != ANICORD_DISCORD_BOT:
            m = f'This message is not from the <@{ANICORD_DISCORD_BOT}>.'

        elif not msg.embeds:
            m = 'This message.... does not have an embed.'

        elif (embed := msg.embeds[0]) and (
            not embed.title or not embed.description or embed.title.lower() != 'cards pulled'
        ):
            if embed.description and not check_pullall_author(msg.author.id, embed.description):
                m = 'This is not your pullall message.'
            else:
                m = 'This message is not the pullall message'

        # These are a lot of checks to avoid yk using the wrong data.
        # The messages are reduces to an amount which isnt much
        # but is enough to convey most of the information required

        fail = m is None

        kwargs = {}

        if ctx.interaction:
            kwargs['ephemeral'] = True

        if m:
            await ctx.reply(m, **kwargs)
        return fail

    return commands.check(predicate)


class GachaUser:
    def __init__(self, timer: Timer | None, *, config_data: asyncpg.Record) -> None:
        self.timer = timer
        self.config_data = config_data
        super().__init__()

    @classmethod
    async def from_fetched_record(
        cls,
        pool: asyncpg.Pool[asyncpg.Record],
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

        return cls(timer, config_data=record)


class GachaReminderView(BaseView):
    def __init__(
        self,
        ctx: Context,
        user: discord.User | discord.Member,
        pull_message: discord.Message | None,
        gacha_user: GachaUser,
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.user = user
        self.pull_message = pull_message
        self.gacha_user = gacha_user
        self.clear_items()

    @classmethod
    async def start(
        cls,
        ctx: Context,
        *,
        user: discord.User | discord.Member,
        pull_message: discord.Message | None,
    ) -> discord.InteractionCallbackResponse[Mafuyu] | discord.Message | None:
        gacha_user = await GachaUser.from_fetched_record(ctx.bot.pool, user=user)

        c = cls(ctx, user, pull_message, gacha_user)

        embed = c.embed()

        return await ctx.reply(embed=embed, view=c, ephemeral=True)

    def embed(self) -> Embed:
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
            s.append(f'> **Next Pull in :** {generate_timestamp_string(next_pull, with_time=True)}')

        return Embed(
            title='Anicord Gacha Bot Helper',
            description=better_string(s, seperator='\n'),
        )

    def _update_display(self) -> None:
        if self.pull_message:
            self.add_item(self.remind_me_button)
        self.remind_me_button.style = discord.ButtonStyle.green if self.gacha_user.timer else discord.ButtonStyle.red

    @discord.ui.button(emoji='\U000023f0', label='Remind me', style=discord.ButtonStyle.gray)
    async def remind_me_button(
        self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]
    ) -> None | discord.InteractionCallbackResponse[Mafuyu]:
        # Bad implementation incoming
        if not self.pull_message:
            # Never will occur
            await interaction.response.defer()
            return None

        if self.gacha_user.timer:
            await self.ctx.bot.timer_manager.cancel_timer(
                user=interaction.user,
                reserved_type=ReservedTimerType.ANICORD_GACHA,
            )
            self.gacha_user.timer = None  # Timer gone.
            return await interaction.response.edit_message(content='Successfully removed pull reminder', embed=self.embed())

        remind_time = self.pull_message.created_at + PULL_INTERVAL

        self.gacha_user.timer = await self.ctx.bot.timer_manager.create_timer(
            remind_time,
            user=interaction.user,
            reserved_type=ReservedTimerType.ANICORD_GACHA,
        )

        return await interaction.response.edit_message(content='Successfully created a pull reminder', embed=self.embed())


class AniCordGacha(BaseCog):
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

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def pull_message_menu(self, interaction: discord.Interaction[Mafuyu], message: discord.Message) -> None:
        interaction.message = message
        check = await pullall_check().predicate(await Context.from_interaction(interaction))
        if check is False:
            return
        await GachaReminderView.start(
            await Context.from_interaction(interaction),
            user=interaction.user,
            pull_message=message,
        )

    @commands.hybrid_group(name='gacha', description='Handles Anicord Gacha Bot', fallback='status')
    @pullall_check()
    async def gacha_group(self, ctx: Context) -> None:
        await GachaReminderView.start(ctx, user=ctx.author, pull_message=None)
