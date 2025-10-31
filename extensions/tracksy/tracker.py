from __future__ import annotations

import re
from typing import TYPE_CHECKING

from discord.ext import commands

from extensions.tracksy.constants import ANICORD_DISCORD_BOT, ANICORD_GACHA_SERVER
from extensions.tracksy.types import PullType
from utilities.bases.cog import CyCog

if TYPE_CHECKING:
    import discord


class Tracker(CyCog):
    @commands.Cog.listener('on_message')
    async def message_listener(self, message: discord.Message) -> None:
        if not (message.author.id == ANICORD_DISCORD_BOT and (message.guild and message.guild.id == ANICORD_GACHA_SERVER)):
            return

    def parse_pull(self, message: discord.Message) -> None:
        """
        Responsible for all parsing and data production from the pulls.

        Parameters
        ----------
        message : discord.Message
            The message to be parsed

        """
        content = message.content
        embed = message.embeds[0]
        title = embed.title
        description = embed.description

        if not (title is not None and description is not None):
            # Embed is clearly not supposed to be a trackable embed
            return

        pull_type = (
            (PullType.SINGLE_PULL if title != 'Weekly Pull Result' else PullType.WEEKLY_PULL)
            if content
            else PullType.PULLALL
            if title == 'Cards Pulled'
            else PullType.PACK
        )
        # This is confirmed to work until the card name itself is meant for it to not work,
        # as in its called "Cards Pulled" this should never happen but if it does,
        # It would have a special case for it. It doesnt for now because there is no need for it

        pull_user = self.parse_author(
            pull_type,
            (content if pull_type in {PullType.SINGLE_PULL, PullType.WEEKLY_PULL} else description)
            if pull_type != PullType.PACK
            else title,
        )
        if not pull_user:
            return

        # TODO: Pulls parser

    def parse_author(
        self,
        pull_type: PullType,
        content: str,
    ) -> discord.User | None:
        """
        Parse author from provided pull content with respect to provided pull type.

        For the sake of reduced complexity inside this function only accepts the content
        that it needs to parse. Pullall is an exception to this in a way but also not really

        Parameters
        ----------
        pull_type : PullType
            The type of pull which will be parsed
        content : str
            Content which will be used to get the author.
            This is usually either the message content or the embed

        Returns
        -------
        User | None
            The User object made from the parsed content.
            This will be None if the bot cannot access the User
            inside its cache

        """
        match pull_type:
            case PullType.PULLALL:
                content = content.splitlines()[0]
                # NOTE: Author is inside the embed description
                author_id_match = int(next(re.finditer(r'<@!?([0-9]+)>', content))[0])

                return self.bot.get_user(author_id_match)

            case PullType.SINGLE_PULL | PullType.WEEKLY_PULL:
                author_id_match = int(next(re.finditer(r'<@!?([0-9]+)>', content))[0])

                return self.bot.get_user(author_id_match)

            case PullType.PACK:
                content = content.replace("'s pack opening!", '')
                # TODO: Use Regex
                user = [_ for _ in self.bot.users if _.global_name == content]
                return user[0] if user else None
