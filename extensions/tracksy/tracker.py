from __future__ import annotations

import re
from typing import TYPE_CHECKING

from discord.ext import commands

from extensions.tracksy.constants import (
    ANICORD_DISCORD_BOT,
    ANICORD_GACHA_SERVER,
    PACK_PULL_REGEX,
    PULLALL_LINE_REGEX,
    RARITY_EMOJIS,
    SINGLE_PULL_REGEX,
    WEEKLY_PULL_REGEX,
)
from extensions.tracksy.types import Card, PullType
from utilities.bases.cog import CyCog

if TYPE_CHECKING:
    import discord

    from utilities.embed import Embed


class Tracker(CyCog):
    # Order of functions:
    # Listener -> Pull parser function -> Functions used in the pull parsers -> Misc
    @commands.Cog.listener('on_message')
    async def message_listener(self, message: discord.Message) -> None:
        if not (message.author.id == ANICORD_DISCORD_BOT and (message.guild and message.guild.id == ANICORD_GACHA_SERVER)):
            return

    async def parse_pull(self, message: discord.Message) -> None:
        """
        Responsible for all parsing and data production from the pulls.

        Parameters
        ----------
        message : discord.Message
            The message to be parsed

        """
        if not message.embeds:
            return

        embed = message.embeds[0]
        content = message.content
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

    async def evaluate_pulls(self, pull_type: PullType, embed: Embed, message: discord.Message) -> list[Card] | None:
        title = embed.title
        description = embed.description

        if not (title is not None and description is not None):
            # Embed is clearly not supposed to be a trackable embed
            return None

        pulls: list[Card] = []

        match pull_type:
            case PullType.PULLALL:
                lines = description.splitlines()

                del lines[0]  # Author line

                for line in lines:
                    parsed_data = next(re.finditer(PULLALL_LINE_REGEX, line)).groupdict()

                    pulls.append(
                        Card(
                            int(parsed_data['id']),
                            parsed_data['name'],
                            {emoji.name: rarity for rarity, emoji in RARITY_EMOJIS.items()}[parsed_data['rarity']],
                        )
                    )
            case PullType.SINGLE_PULL:
                parsed_data = next(re.finditer(SINGLE_PULL_REGEX, description)).groupdict()

                pulls.append(
                    Card(
                        int(parsed_data['id']),
                        title,
                        {emoji.name: rarity for rarity, emoji in RARITY_EMOJIS.items()}[parsed_data['rarity']],
                    )
                )
            case PullType.WEEKLY_PULL:
                parsed_data = next(re.finditer(WEEKLY_PULL_REGEX, description)).groupdict()

                pulls.append(
                    Card(
                        int(parsed_data['id']),
                        parsed_data['name'],
                        {emoji.name: rarity for rarity, emoji in RARITY_EMOJIS.items()}[parsed_data['rarity']],
                    )
                )
            case PullType.PACK:
                # NOTE: Tracking for packs is... basically its not instant, There is a wait_for involved,
                # No performance cost just its not a continuoud function
                footer = embed.footer.text
                if footer is None:
                    return None

                total_pages = int(footer.split('/')[-1])

                pack_pulls: dict[int, Card] = {}

                def evaluate_pull_from_pack_page(pg: int, desc: str) -> None:
                    parsed_data = next(re.finditer(PACK_PULL_REGEX, desc)).groupdict()

                    pack_pulls[pg] = Card(
                        int(parsed_data['id']),
                        parsed_data['name'],
                        {emoji.name: rarity for rarity, emoji in RARITY_EMOJIS.items()}[parsed_data['rarity']],
                    )

                page = int(footer.split('/', maxsplit=1)[0])

                evaluate_pull_from_pack_page(page, description)

                while True:

                    def check(msg: discord.Message) -> bool:
                        return msg.id == message.id

                    try:
                        _, post_edit_message = await self.bot.wait_for('message_edit', timeout=60.0, check=check)

                    except TimeoutError:
                        break

                    else:
                        post_edit_embed: Embed | None = post_edit_message.embeds[0] if post_edit_message.embeds else None
                        if (
                            not post_edit_embed
                            or not post_edit_embed.description
                            or not post_edit_embed.title
                            or not post_edit_embed.footer.text
                        ):
                            break  # Getting types out of the way

                        page = int(post_edit_embed.footer.text.split('/', maxsplit=1)[0])

                        evaluate_pull_from_pack_page(page, post_edit_embed.description)

                        if page == total_pages:
                            break
                        continue

                pulls.extend(list(pack_pulls.values()))

        # We have accounted for all the pulls now.
        return pulls
