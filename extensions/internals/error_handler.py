from __future__ import annotations

import contextlib
import datetime
import difflib
import inspect
import logging
import operator
from typing import TYPE_CHECKING, Any, Self

import discord
from discord.ext import commands, menus

from utilities.bases.cog import ElyCog
from utilities.constants import ERROR_COLOUR, BotEmojis
from utilities.embed import Embed
from utilities.errors import ElysiaError, WaifuNotFoundError
from utilities.functions import fmt_str, format_tb, get_command_signature
from utilities.pagination import Paginator
from utilities.view import BaseView

if TYPE_CHECKING:
    from asyncpg import Record

    from utilities.bases.bot import Elysia
    from utilities.bases.context import ElyContext
log = logging.getLogger(__name__)


class Argument:
    is_provided: bool = False

    def __init__(self, *, value: str | None, param: commands.Parameter) -> None:
        self.value: Any = value
        self.param: commands.Parameter = param
        super().__init__()

    def to_option(self) -> discord.SelectOption:
        name = self.param.displayed_name or self.param.name
        emoji = (
            BotEmojis.GREY_TICK
            if self.param.required is False and self.is_provided is False
            else (BotEmojis.GREEN_TICK if self.is_provided else BotEmojis.RED_CROSS)
        )
        return discord.SelectOption(
            emoji=emoji,
            label=f'{name}{" [required]" if self.param.required else ""}',
            value=self.param.name,
            description='\n'.join(
                _
                for _ in [
                    self.param.description,
                    ('(Default: ' + str(self.param.default if self.param.default is not None else 'Nothing') + ')')
                    if self.param.default is not inspect._empty and self.param.required is False  # pyright: ignore[reportPrivateUsage]
                    else '',
                ]
                if _
            ),
        )


class CommandInvokeView(BaseView):
    def __init__(self, *, ctx: ElyContext, command: commands.Command[Any, Any, Any]) -> None:
        super().__init__(timeout=180.0)
        self.ctx = ctx
        self.command = command
        if self.run_command.label:
            self.run_command.label += self.command.name

    @discord.ui.button(label='Run ', style=discord.ButtonStyle.gray, emoji=BotEmojis.GREY_TICK)
    async def run_command(
        self, interaction: discord.Interaction[Elysia], _: discord.ui.Button[Self]
    ) -> discord.InteractionCallbackResponse[Elysia] | None:
        can_run = False

        try:
            self.ctx.command = (
                self.command
            )  # Since we have the correct command. Running can_run without giving ctx the command loops the error
            await self.ctx.bot.invoke(self.ctx)
            can_run = True

        except Exception as err:
            self.ctx.bot.dispatch('command_error', self.ctx, err)

        with contextlib.suppress(discord.HTTPException):
            if self.message:
                await self.message.delete()

        if can_run:
            return None

        # NOTE: There isn't any case this should run, i believe.

        invoked_with: list[Any] = []
        if self.ctx.current_argument:
            for param in self.command.params.values():
                converted = await commands.run_converters(
                    self.ctx,
                    param.converter,
                    self.ctx.current_argument,
                    param,
                )
                invoked_with.append(converted)

        await self.ctx.invoke(self.command, *invoked_with)
        return await interaction.response.defer()

    async def interaction_check(self, interaction: discord.Interaction[Elysia]) -> bool:
        return interaction.user == self.ctx.author


class MissingArgumentModal(discord.ui.Modal):
    argument_value: discord.ui.TextInput[MissingArgumentHandler] = discord.ui.TextInput(
        label='Enter the Missing Argument,',
        style=discord.TextStyle.long,
        placeholder='...',
        required=True,
        max_length=2000,
    )

    def __init__(
        self,
        argument: Argument,
        handler: MissingArgumentHandler,
        *,
        title: str,
        timeout: float | None = None,
        previous_message: discord.Message,
    ) -> None:
        self.argument: Argument = argument
        self.handler: MissingArgumentHandler = handler
        self.prev_message = previous_message
        super().__init__(title=title, timeout=timeout)

    async def on_submit(
        self, interaction: discord.Interaction[Elysia]
    ) -> discord.InteractionCallbackResponse[Elysia] | None:
        try:
            converted = await commands.run_converters(
                self.handler.ctx,
                self.argument.param.converter,
                self.argument_value.value,
                self.argument.param,
            )
        except commands.UserInputError as exc:
            await self.handler.prev_message.delete()
            self.handler.ctx.bot.dispatch('command_error', self.handler.ctx, exc)
            await interaction.response.defer()
            return
        self.handler.arguments[self.argument.param.name].value = converted
        self.handler.arguments[self.argument.param.name].is_provided = True
        self.handler.handle_components()
        await interaction.response.edit_message(view=self.handler)


class MissingArgumentHandler(discord.ui.View):
    prev_message: discord.Message

    def __init__(
        self,
        error: commands.MissingRequiredArgument,
        ctx: ElyContext,
        *,
        timeout: float | None = 180,
    ) -> None:
        self.error = error
        self.ctx = ctx
        super().__init__(timeout=timeout)

        self.arguments: dict[str, Argument] = self.collect_parameters_and_arguments()
        self.handle_components()

    def handle_components(self) -> None:
        arguments = self.arguments.values()
        self.argument_selector.options = [argument.to_option() for argument in arguments]

    def get_invoke_args(self) -> tuple[tuple[Any, ...], dict[str, Any]]:
        if not self.arguments:
            return (), {}

        args: list[Any] = []
        kwargs: dict[str, Any] = {}
        for argument in self.arguments.values():
            if argument.param.kind is inspect._ParameterKind.POSITIONAL_ONLY:  # pyright: ignore[reportPrivateUsage]
                args.append(argument.value)
            elif (
                argument.param.kind is inspect._ParameterKind.POSITIONAL_OR_KEYWORD  # pyright: ignore[reportPrivateUsage]
                or argument.param.kind is inspect._ParameterKind.KEYWORD_ONLY  # pyright: ignore[reportPrivateUsage]
            ):
                kwargs[argument.param.name] = argument.value

        return tuple(args), kwargs

    def collect_parameters_and_arguments(self) -> dict[str, Argument]:
        assert self.ctx.command is not None
        parameters: dict[str, commands.Parameter] = self.ctx.command.clean_params
        signature: inspect.Signature = inspect.signature(self.ctx.command.callback)
        bind_arguments: inspect.BoundArguments = signature.bind_partial(*self.ctx.args, **self.ctx.kwargs)
        bind_arguments.apply_defaults()
        arguments: dict[str, Argument] = {}

        for param in parameters.values():
            value = bind_arguments.arguments.get(param.name, None)

            if isinstance(value, commands.Parameter):
                value = value.default

            arguments[param.name] = Argument(
                value=value,
                param=param,
            )

        return arguments

    @discord.ui.select(
        placeholder='Select an argument to add',
    )
    async def argument_selector(self, interaction: discord.Interaction[Elysia], _: discord.ui.Select[Self]) -> None:
        modal = MissingArgumentModal(
            argument=self.arguments[self.argument_selector.values[0]],
            handler=self,
            title=self.error.param.displayed_name or self.error.param.name,
            previous_message=self.prev_message,
        )
        modal.prev_message = self.prev_message
        await interaction.response.send_modal(modal)

        await modal.wait()

        if all(argument.value for argument in self.arguments.values() if argument.param.required):
            with contextlib.suppress(discord.HTTPException):
                if self.prev_message:
                    await self.prev_message.delete()

            cmd = self.ctx.command
            if not cmd:
                await interaction.response.send_message('Something went wrong', ephemeral=True)
                msg = 'Command not found. This should not happen.'
                raise TypeError(msg)
            args, kwargs = self.get_invoke_args()
            try:
                await self.ctx.invoke(cmd, *args, **kwargs)
            except Exception as err:
                self.ctx.bot.dispatch('command_error', self.ctx, err)

    async def interaction_check(self, interaction: discord.Interaction[Elysia]) -> bool:
        return interaction.user == self.ctx.author


class ErrorView(BaseView):
    def __init__(self, error_record: Record, ctx: ElyContext) -> None:
        self.error_record = error_record
        self.ctx = ctx
        super().__init__()

    @discord.ui.button(label='Wanna know more?', style=discord.ButtonStyle.grey)
    async def inform_button(self, interaction: discord.Interaction[Elysia], _: discord.ui.Button[Self]) -> None:
        embed = Embed(
            description=f'```py\n{self.error_record["error"]}```',
            colour=ERROR_COLOUR,
        )
        error_timestamp: datetime.datetime = self.error_record['occured_when']
        is_fixed = 'is not' if self.error_record['fixed'] is False else 'is'
        embed.add_field(
            value=(
                f'The error was discovered **{discord.utils.format_dt(error_timestamp, "R")}** '
                f'in the **{self.error_record["command"]}** command and **{is_fixed}** fixed'
            )
        )
        embed.set_footer(
            text=f'Requested by {interaction.user}',
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_author(
            name=f'Error #{self.error_record["id"]}',
            icon_url=BotEmojis.RED_CROSS.url,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Get notified', style=discord.ButtonStyle.green)
    async def notified_button(self, interaction: discord.Interaction[Elysia], _: discord.ui.Button[Self]) -> None:
        is_user_present = await interaction.client.pool.fetchrow(
            """SELECT * FROM ErrorReminders WHERE id = $1 AND user_id = $2""",
            self.error_record['id'],
            interaction.user.id,
        )

        if is_user_present:
            await interaction.client.pool.execute(
                """DELETE FROM ErrorReminders WHERE id = $1 AND user_id = $2""",
                self.error_record['id'],
                interaction.user.id,
            )
            await interaction.response.send_message(
                'You will no longer be notified when this error is fixed.',
                ephemeral=True,
            )
            return

        await interaction.client.pool.execute(
            """INSERT INTO ErrorReminders (id, user_id) VALUES ($1, $2)""",
            self.error_record['id'],
            interaction.user.id,
        )
        await interaction.response.send_message('You will now be notified when this error is fixed', ephemeral=True)


class ErrorPageSource(menus.ListPageSource):
    def __init__(self, bot: Elysia, entries: list[Record]) -> None:
        self.bot = bot
        entries = sorted(entries, key=operator.itemgetter('id'))
        super().__init__(entries, per_page=1)

    async def format_page(self, _: Paginator, entry: Record) -> Embed:
        embed = await Embed.logger(self.bot, entry)
        embed.title = embed.title + f'/{self.get_max_pages()}' if embed.title else None
        return embed


class ErrorHandler(ElyCog):
    default_errors = (
        commands.UserInputError,
        commands.DisabledCommand,
        commands.MaxConcurrencyReached,
        commands.CommandOnCooldown,
        commands.PrivateMessageOnly,
        commands.NoPrivateMessage,
        commands.NotOwner,
        commands.NSFWChannelRequired,
        commands.TooManyArguments,
        commands.CheckFailure,
    )

    def _cleanse_error_attrs(self, attrs: list[str] | str, *, seperator: str, prefix: str) -> str:
        return (
            fmt_str(
                (prefix + f'{(perm.replace("_", " ")).capitalize()}' for perm in attrs),
                seperator=seperator,
            )
            if type(attrs) is not str
            else prefix + attrs
        )

    def _fix_error_iter(
        self,
        error: (
            commands.MissingPermissions
            | commands.BotMissingPermissions
            | commands.MissingAnyRole
            | commands.MissingRole
            | commands.BotMissingAnyRole
            | commands.BotMissingRole
        ),
    ) -> list[str]:
        m: list[str] = []

        if isinstance(error, commands.MissingRole | commands.BotMissingRole):
            m.append(str(f'<@&{error.missing_role}>' if type(error.missing_role) is int else error.missing_role))

        elif isinstance(error, commands.MissingAnyRole | commands.BotMissingAnyRole):
            m.extend([str(f'<@&{role_id}>' if role_id is int else role_id) for role_id in error.missing_roles])

        else:
            m.extend(error.missing_permissions)

        return m

    async def _find_closest_command(self, ctx: ElyContext, name: str) -> commands.Command[None, ..., Any] | None:
        closest_cmd_name = difflib.get_close_matches(
            name,
            [_command.name for _command in self.bot.commands],
            n=1,
        )
        if closest_cmd_name:
            cmd = self.bot.get_command(closest_cmd_name[0])
            if cmd:
                try:
                    can_run = await cmd.can_run(ctx)
                except (commands.CheckAnyFailure, commands.CheckFailure):
                    can_run = False
                if can_run:
                    return cmd
        return None

    async def _log_error(
        self,
        error: commands.CommandError,
        *,
        name: str,
        author: discord.User | discord.Member,
        message: discord.Message,
        guild: discord.Guild | None = None,
    ) -> Record:
        formatted_error = format_tb(error)
        time_occured = datetime.datetime.now()

        record = await self.bot.pool.fetchrow(
            """
                INSERT INTO
                    Errors (
                        command,
                        user_id,
                        guild,
                        error,
                        full_error,
                        message_url,
                        occured_when,
                        fixed
                    )
                VALUES
                    ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
        """,
            name,
            author.id,
            guild.id if guild else None,
            str(error),
            formatted_error,
            message.jump_url,
            time_occured,
            False,
        )

        if not record:
            raise ValueError

        embed = await Embed.logger(self.bot, record)

        await self.bot.logger.send(embed=embed)

        return record

    async def _is_known_error(
        self,
        error: commands.CommandError,
        *,
        command_name: str,
    ) -> Record | None:
        return await self.bot.pool.fetchrow(
            """
                SELECT
                    *
                FROM
                    Errors
                WHERE
                    command = $1
                    AND error = $2
                    AND fixed = $3
            """,
            command_name,
            str(error),
            False,
        )

    @commands.Cog.listener('on_command_error')
    async def error_handler(self, ctx: ElyContext, error: commands.CommandError) -> None | discord.Message:
        if (
            (ctx.command and ctx.command.has_error_handler())
            or (ctx.cog and ctx.cog.has_error_handler())
            or isinstance(error, ElysiaError)
        ):
            return None

        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandNotFound) or not ctx.command:
            if self.bot.is_blacklisted(ctx.author):
                return None
            cmd = ctx.invoked_with
            if not cmd:
                return None

            possible_commands = await self._find_closest_command(ctx, cmd)
            if possible_commands:
                view = CommandInvokeView(ctx=ctx, command=possible_commands)

                cmd_name = await commands.clean_content(escape_markdown=True).convert(ctx, cmd)

                view.message = await ctx.reply(
                    f"Couldn't find a command named `{cmd_name}`. Perhaps, you meant `{possible_commands.name}`?",
                    view=view,
                )

            return None

        if isinstance(error, commands.MissingRequiredArgument | commands.MissingRequiredAttachment):
            param_name = error.param.displayed_name or error.param.name
            embed = Embed.error(
                title=f'Missing {param_name} argument!',
                description=fmt_str(
                    (
                        f'You did not provide a **__{param_name}__** argument.',
                        f'> -# `{get_command_signature(ctx, ctx.command)}`',
                    ),
                    seperator='\n',
                ),
            )
            embed.set_footer(text='The command will be executed as soon as all required arguments have been provided')

            if isinstance(error, commands.MissingRequiredArgument):
                view = MissingArgumentHandler(error, ctx)
                view.prev_message = await ctx.reply(embed=embed, view=view)
            else:
                await ctx.reply(embed=embed)

            return None

        if isinstance(
            error,
            commands.MissingPermissions
            | commands.BotMissingPermissions
            | commands.MissingAnyRole
            | commands.MissingRole
            | commands.BotMissingAnyRole
            | commands.BotMissingRole,
        ):
            subject = (
                'You are'
                if isinstance(
                    error,
                    commands.MissingPermissions | commands.MissingAnyRole | commands.MissingRole,
                )
                else 'I am'
            )

            error_type_wording = (
                'permissions' if isinstance(error, commands.MissingPermissions | commands.BotMissingPermissions) else 'roles'
            )

            final_iter = self._fix_error_iter(error)

            content = fmt_str(
                (
                    f'{subject} missing the following {error_type_wording} to run this command:',
                    self._cleanse_error_attrs(final_iter, seperator='\n', prefix='- '),
                ),
                seperator='\n',
            )

            embed = Embed.error(
                title=f'Missing {error_type_wording.title()}',
                description=content,
            )

            return await ctx.reply(embed=embed)

        if isinstance(error, self.default_errors):
            return await ctx.reply(
                str(error),
                delete_after=getattr(error, 'retry_after', None),
            )

        log.error(
            'Ignoring exception in running %s',
            ctx.command,
            exc_info=error,
        )

        record = await self._is_known_error(
            error,
            command_name=ctx.command.qualified_name,
        )

        if not record:
            record = await self._log_error(
                error,
                name=ctx.command.qualified_name,
                author=ctx.author,
                message=ctx.message,
                guild=ctx.guild,
            )

        view = ErrorView(record, ctx)
        view.message = await ctx.reply(
            embed=Embed.error(
                title='Error occured',
                description='The command borked.',
            ),
            view=view,
        )

        return None

    @commands.Cog.listener('on_command_error')
    async def custom_errors_handler(self, ctx: ElyContext, error: ElysiaError | Exception) -> None | discord.Message:
        if (
            (ctx.command and ctx.command.has_error_handler())
            or (ctx.cog and ctx.cog.has_error_handler())
            or not isinstance(error, ElysiaError)
        ):
            return None

        if isinstance(error, WaifuNotFoundError):
            return await ctx.reply(
                content=(
                    f'Cannot find any results for {error.waifu}.\n'
                    '-# You can only search for a **character** or **franchise/series**.'
                )
            )
        return None

    @commands.group(
        name='error',
        description='Handles all things related to error handler logging.',
        invoke_without_command=True,
    )
    async def errorcmd_base(self, ctx: ElyContext) -> None:
        await ctx.send_help(ctx.command)

    @errorcmd_base.command(name='show', description='Shows the embed for a certain error')
    async def error_show(self, ctx: ElyContext, error_id: int | None = None) -> None:
        if error_id:
            error_record = await self.bot.pool.fetchrow("""SELECT * FROM Errors WHERE id = $1""", error_id)
            if not error_record:
                await ctx.reply('Error not found.')
                return
            embed = await Embed.logger(self.bot, error_record)
            await ctx.reply(embed=embed)
            return
        errors = await self.bot.pool.fetch(
            """SELECT * FROM Errors""",
        )
        paginate = Paginator(ErrorPageSource(self.bot, errors), ctx=ctx)
        await paginate.start()

    @errorcmd_base.command(name='fix', description='Mark an error as fixed')
    async def error_fix(self, ctx: ElyContext, error_id: int) -> None:
        data = await self.bot.pool.fetchrow("""SELECT * FROM Errors WHERE id = $1""", error_id)
        if not data:
            await ctx.reply(f'Cannot find an error with the ID: `{error_id}`')
            return
        await self.bot.pool.execute("""UPDATE Errors SET fixed = $1 WHERE id = $2""", True, error_id)
        notifiers = await self.bot.pool.fetch("""SELECT user_id FROM ErrorReminders WHERE id = $1""", error_id)
        if notifiers:
            users = [_ for _ in [self.bot.get_user(user['user_id']) for user in notifiers] if _]
            for user in users:
                try:
                    await user.send(f'Hey! Error `#{data["id"]}` in the `{data["command"]}` command has been fixed.')
                except discord.errors.Forbidden:
                    continue
            # Assuming all goes fine
            await self.bot.pool.execute("""DELETE FROM ErrorReminders WHERE id = $1""", error_id)
        await ctx.message.add_reaction(BotEmojis.GREEN_TICK)
