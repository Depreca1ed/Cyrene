from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any, TypeVar

import discord
import jishaku
import mystbin
from discord.ext import commands

import config

from . import BASE_COLOUR

if TYPE_CHECKING:
    from collections.abc import Iterable

    import aiohttp
    import asyncpg

    from . import BlacklistData


__all__ = (
    'Context',
    'Mafuyu',
)

log = logging.getLogger('Mafuyu')


jishaku.Flags.FORCE_PAGINATOR = True
jishaku.Flags.HIDE = True
jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.NO_UNDERSCORE = True

C = TypeVar('C', bound='Context')


class Context(commands.Context['Mafuyu']):
    @discord.utils.copy_doc(commands.Context['Mafuyu'].reply)
    async def reply(self, content: str | None = None, **kwargs: Any) -> discord.Message:
        try:
            return await super().reply(content=content, **kwargs)
        except discord.HTTPException:
            return await super().send(content=content, **kwargs)

    @discord.utils.copy_doc(commands.Context['Mafuyu'].send)
    async def send(
        self,
        content: None | str = None,
        **kwargs: Any,
    ) -> discord.Message:
        if content and len(content) > 1990:  # 2000 sounds a bit extreme to edge, safe at 1990
            paste = await self.bot.create_paste(f'Requested by {self.author}', content=content)
            content = (
                'The response which was supposed to be here was too big. I have posted it to MystBin instead\n'
                f'-# Link: {paste.url}'
            )

        return await super().send(
            content=content,
            **kwargs,
        )


async def _callable_prefix(bot: Mafuyu, message: discord.Message) -> list[str]:
    prefixes = commands.when_mentioned(bot, message)

    prefixes.extend(bot.get_prefixes(message.guild))

    return prefixes


class Mafuyu(commands.AutoShardedBot):
    pool: asyncpg.Pool[asyncpg.Record]
    user: discord.ClientUser

    def __init__(
        self,
        *,
        extensions: list[str],
        intents: discord.Intents,
        allowed_mentions: discord.AllowedMentions,
        session: aiohttp.ClientSession,
    ) -> None:
        super().__init__(
            command_prefix=_callable_prefix,
            case_insensitive=True,
            strip_after_prefix=True,
            intents=intents,
            allowed_mentions=allowed_mentions,
            enable_debug_events=True,
            help_command=commands.MinimalHelpCommand(),
        )

        self.prefixes: dict[int, list[str]] = {}
        self.blacklists: dict[int, BlacklistData] = {}

        self.session = session
        self.mystbin = mystbin.Client(session=self.session)
        self.start_time = datetime.datetime.now()
        self.colour = self.color = BASE_COLOUR
        self.initial_extensions = extensions

    async def setup_hook(self) -> None:
        await self.refresh_bot_variables()

        await self.load_extensions(self.initial_extensions)
        await self.load_extension('jishaku')

    async def get_context(self, origin: discord.Message | discord.Interaction, *, cls: type[Context] = Context) -> Context:
        return await super().get_context(origin, cls=cls)

    async def is_owner(self, user: discord.abc.User) -> bool:
        return bool(user.id in config.OWNERS_ID)

    async def load_extensions(self, extensions: Iterable[str]) -> None:
        """
        Load all extensions for the bot.

        Parameters
        ----------
        extensions : Iterable[str]
            The list of extensions to be loaded

        """
        for extension in extensions:
            try:
                await self.load_extension(extension)
            except commands.ExtensionFailed as exc:
                log.exception('An exception occured while loading extension: %s', extension, exc_info=exc)
            else:
                log.info('Loaded %s', extension)

    async def unload_extensions(self, extensions: Iterable[str]) -> None:
        """
        Unload all extensions for the bot.

        Parameters
        ----------
        extensions : Iterable[str]
            The list of extensions to be unloaded

        """
        for extension in extensions:
            await self.unload_extension(extension)

    async def reload_extensions(self, extensions: Iterable[str]) -> None:
        """
        Reload all extensions for the bot.

        Parameters
        ----------
        extensions : Iterable[str]
            The list of extensions to be reloaded

        """
        for extension in extensions:
            await self.reload_extension(extension)

    def get_prefixes(self, guild: discord.Guild | None) -> list[str]:
        """
        Get a list of prefixes for a guild if given.

        Defaults to base prefix

        Parameters
        ----------
        guild : discord.Guild | None
            The guild to get prefixes of.

        Returns
        -------
        list[str]
            A list of prefixes for a guild if provided. Defaults to base prefix

        """
        return self.prefixes.get(guild.id, [config.DEFAULT_PREFIX]) if guild else [config.DEFAULT_PREFIX]

    def is_blacklisted(self, snowflake: discord.User | discord.Member | discord.Guild | int) -> BlacklistData | None:
        """
        Check if a user or guild is blacklisted.

        This function is also used as a get

        Parameters
        ----------
        snowflake : discord.User | discord.Member | discord.Guild
            The snowflake to be checked

        Returns
        -------
        BlacklistData | None
            The blacklist data of the snowflake

        """
        return self.blacklists.get(snowflake if isinstance(snowflake, int) else snowflake.id, None)

    async def create_paste(self, filename: str, content: str) -> mystbin.Paste:
        """
        Create a mystbin paste.

        Parameters
        ----------
        filename : str
            The name of the file in paste
        content : str
            The contents of the file

        Returns
        -------
        mystbin.Paste
            The created paste

        """
        file = mystbin.File(filename=filename, content=content)
        return await self.mystbin.create_paste(files=[file])

    async def refresh_bot_variables(self) -> None:
        """Set values to some bot constants."""
        self._support_invite = await self.fetch_invite('https://discord.gg/mtWF6sWMex')

        self.appinfo = await self.application_info()

    @property
    def owner(self) -> discord.TeamMember | discord.User:
        """
        Return the user object of the owner of the bot.

        Returns
        -------
        discord.TeamMember | discord.User
            The owner's TeamMember or User object.

        """
        return self.appinfo.team.owner if self.appinfo.team and self.appinfo.team.owner else self.appinfo.owner

    @discord.utils.cached_property
    def logger(self) -> discord.Webhook:
        """
        Return webhook logger used for sending certain logs to a channel.

        Returns
        -------
        discord.Webhook
            The webhook used.

        """
        return discord.Webhook.from_url(config.WEBHOOK, session=self.session)

    @property
    def support_invite(self) -> discord.Invite:
        """
        Return invite to the support server.

        Returns
        -------
        discord.Invite
            The invite link object

        """
        return self._support_invite

    @discord.utils.cached_property
    def invite_url(self) -> str:
        """
        Return invite link to invite the bot.

        Returns
        -------
        str
            The generated link

        """
        return discord.utils.oauth_url(self.user.id, scopes=None)

    @property
    def humanized_start_time(self) -> str:
        """
        Return a humanized form of the bot's uptime.

        Returns
        -------
        str
            The humanized uptime

        """
        return discord.utils.format_dt(self.start_time, 'R')

    async def close(self) -> None:
        if hasattr(self, 'pool'):
            await self.pool.close()
        if hasattr(self, 'session'):
            await self.session.close()
        await super().close()

    @property
    def config(self):  # noqa: ANN201
        return __import__('config')
