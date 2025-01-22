from __future__ import annotations

import datetime
import logging
from typing import Self, TypeVar

import aiohttp
import asyncpg
import discord
import jishaku
import mystbin
from discord.ext import commands
from topgg.client import DBLClient
from topgg.webhook import WebhookManager

import config
from utils import BASE_COLOUR, BlacklistBase, Context

__all__ = ('Mafuyu',)

log: logging.Logger = logging.getLogger(__name__)


extensions = [
    'extensions.animanga',
    'extensions.internals',
    'extensions.meta',
    'extensions.private',
]

jishaku.Flags.FORCE_PAGINATOR = True
jishaku.Flags.HIDE = True
jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.NO_UNDERSCORE = True

C = TypeVar('C', bound='Context')


async def _callable_prefix(bot: Mafuyu, message: discord.Message) -> list[str]:
    base = commands.when_mentioned(bot, message)

    if not message.guild:
        base.append(config.DEFAULT_PREFIX)

    else:
        base.extend(bot.get_guild_prefixes(message.guild))

    return base


class Mafuyu(commands.Bot):
    pool: asyncpg.Pool[asyncpg.Record]
    user: discord.ClientUser

    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.all()
        allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=True)

        super().__init__(
            command_prefix=_callable_prefix,
            case_insensitive=True,
            strip_after_prefix=True,
            intents=intents,
            max_messages=5000,
            allowed_mentions=allowed_mentions,
            help_command=commands.MinimalHelpCommand(),
        )

        self.token = config.TOKEN

        self.prefixes: dict[int, list[str]] = {}
        self.blacklist: dict[int, BlacklistBase] = {}

        self.maintenance: bool = False
        self.start_time = datetime.datetime.now()
        self.reload_time: datetime.datetime | None = None
        self.colour = self.color = BASE_COLOUR
        self.initial_extensions = extensions
        self.context_class: type[commands.Context[Self]] = commands.Context

    async def setup_hook(self) -> None:
        pool = await asyncpg.create_pool(config.DATABASE_CRED)
        if not pool or (pool and pool.is_closing()):
            msg = 'Failed to setup PostgreSQL. Shutting down.'
            raise RuntimeError(msg)

        self.pool = pool

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
        )
        self.mystbin = mystbin.Client(session=self.session)

        await self.refresh_bot_variables()

        self.topgg = DBLClient(self, config.TOPGG, autopost=True, post_shard_count=True)
        self.topgg_webhook = WebhookManager(self).dbl_webhook('/debotdbl').run(1234)

        for cog in self.initial_extensions:
            try:
                await self.load_extension(str(cog))
            except commands.ExtensionError as error:
                log.exception(
                    'Failed to load %s',
                    cog,
                    exc_info=error,
                )
            else:
                log.info('Successfully loaded %s', cog)
        await self.load_extension('jishaku')

    def get_guild_prefixes(self, guild: discord.Guild) -> list[str]:
        return self.prefixes.get(guild.id, [config.DEFAULT_PREFIX])

    def is_blacklisted(self, snowflake: discord.User | discord.Member | discord.Guild) -> BlacklistBase | None:
        return self.blacklist.get(snowflake.id, None)

    async def get_context(self, message: discord.Message, *, cls: type[C] | None = None) -> Context | commands.Context[Self]:
        new_cls = cls or self.context_class
        return await super().get_context(message, cls=new_cls)

    async def create_paste(self, filename: str, content: str) -> mystbin.Paste:
        file = mystbin.File(filename=filename, content=content)
        return await self.mystbin.create_paste(files=[file])

    async def refresh_bot_variables(self) -> None:
        self.bot_emojis = {emoji.name: emoji for emoji in await self.fetch_application_emojis()}
        self._support_invite = await self.fetch_invite('https://discord.gg/mtWF6sWMex')
        self.appinfo = await self.application_info()

    async def reload_extension(self, name: str | None, *, package: str | None = None) -> None:
        if name:
            await super().reload_extension(name, package=package)
            return
        for ext in self.initial_extensions:
            await super().reload_extension(ext, package=package)  # Not sure what package implies but okay
        return

    @property
    def owner(self) -> discord.User:
        return self.appinfo.owner

    @discord.utils.copy_doc(commands.Bot.is_owner)
    async def is_owner(self, user: discord.abc.User) -> bool:
        return bool(user.id in config.OWNERS_ID)

    @discord.utils.cached_property
    def logger_webhook(self) -> discord.Webhook:
        return discord.Webhook.from_url(config.WEBHOOK, session=self.session)

    @discord.utils.cached_property
    def guild(self) -> discord.Guild:
        guild = self.get_guild(1262409199552430170)
        if not guild:
            msg = 'Support server not found'
            raise commands.GuildNotFound(msg)
        return guild

    @property
    def support_invite(self) -> discord.Invite:
        return self._support_invite

    @discord.utils.cached_property
    def invite_url(self) -> str:
        return discord.utils.oauth_url(self.user.id, scopes=None)

    @property
    def topgg_url(self) -> str:
        return f'https://top.gg/bot/{self.user.id}'

    async def close(self) -> None:
        if hasattr(self, 'pool'):
            await self.pool.close()
        if hasattr(self, 'session'):
            await self.session.close()
        if hasattr(self, 'topgg'):
            await self.topgg.close()
        if hasattr(self, 'topgg_webhook'):
            self.topgg_webhook.cancel()
        await super().close()

    @property
    def config(self):  # noqa: ANN201
        return __import__('config')
