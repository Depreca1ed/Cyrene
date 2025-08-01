from __future__ import annotations  # noqa: N999

import enum
from typing import TYPE_CHECKING, Self

import discord
from discord.ext import commands

from config import SUGGESTIONS_WEBHOOK_TOKEN
from utilities.bases.cog import MafuCog
from utilities.constants import BotEmojis
from utilities.embed import Embed
from utilities.view import BaseView

if TYPE_CHECKING:
    from utilities.bases.bot import Mafuyu
    from utilities.bases.context import MafuContext


class SuggestionCategories(enum.Enum):
    NEW_FEATURE = 1
    BUG_FIX = 2
    CHANGE = 3
    MISC = 4


class ADGSuggestionView(BaseView):
    def __init__(self, user: discord.User | discord.Member) -> None:
        super().__init__()
        self.user = user
        self.suggestion_data: dict[str, str | None] = {
            'category': None,
            'title': None,
            'description': None,
            'status': '1',
        }

    @classmethod
    async def start(
        cls,
        ctx: MafuContext,
        user: discord.User | discord.Member,
    ) -> None:
        c = cls(user)

        embed = c.embed()
        c.update_display()

        message = await ctx.reply(embed=embed, view=c)
        c.message = message

    def embed(self) -> Embed:
        embed = Embed(
            title=self.suggestion_data['title'] or 'Placeholder title',
            description=self.suggestion_data['description'] or 'Placeholder description',
            colour=0xFFFFFF,
        )

        embed.set_author(name=f'From {self.user.name}', icon_url=self.user.display_avatar.url)

        if self.suggestion_data['category']:
            embed.add_field(
                value='- **Category:** '
                + SuggestionCategories._value2member_map_[
                    int(
                        self.suggestion_data['category'],
                    )
                ]
                .name.replace(
                    '_',
                    ' ',
                )
                .title()
            )

        return embed

    def update_display(self) -> None:
        self.clear_items()
        self.add_item(self.cancel_button)
        self.add_item(self.write_suggestion)
        self.add_item(self.category_select)
        if (
            self.suggestion_data['category'] is not None
            and self.suggestion_data['title'] is not None
            and self.suggestion_data['description'] is not None
        ):
            self.add_item(self.send_suggestion)

    @discord.ui.select(
        placeholder='Select suggestion category',
        min_values=1,
        max_values=1,
        row=2,
        options=[
            discord.SelectOption(label=a.name.replace('_', ' ').title(), value=str(a.value)) for a in SuggestionCategories
        ],
    )
    async def category_select(self, interaction: discord.Interaction[Mafuyu], s: discord.ui.Select[Self]) -> None:
        val = s.values[0]
        self.suggestion_data['category'] = val

        self.update_display()
        e = self.embed()

        await interaction.response.edit_message(embed=e, view=self)

    @discord.ui.button(emoji=BotEmojis.RED_CROSS, style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        await interaction.response.defer()
        self.stop()
        await interaction.delete_original_response()

    @discord.ui.button(emoji='\U0000270d', style=discord.ButtonStyle.gray)
    async def write_suggestion(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        await interaction.response.send_modal(ADGSuggestionModal(view=self))

    @discord.ui.button(emoji=BotEmojis.GREEN_TICK, style=discord.ButtonStyle.green)
    async def send_suggestion(self, interaction: discord.Interaction[Mafuyu], _: discord.ui.Button[Self]) -> None:
        embed = self.embed()

        webhook = discord.Webhook.from_url(SUGGESTIONS_WEBHOOK_TOKEN, session=interaction.client.session)

        msg = await webhook.send(embed=embed, wait=True)

        # Now we write all this data to db

        query = """
                INSERT INTO
                    ADGSuggestions (
                        user_id,
                        feature_category,
                        feature_title,
                        feature_description,
                        webhook_message,
                        feature_status
                    )
                VALUES
                    ($1, $2, $3, $4, $5, $6);
                """

        await interaction.client.pool.execute(
            query,
            self.user.id,
            int(str(self.suggestion_data['category'])),
            self.suggestion_data['title'],
            self.suggestion_data['description'],
            msg.id,
            int(str(self.suggestion_data['status'])),
        )
        await interaction.response.edit_message(content='Suggestion has been successfully sent', embed=None, view=None)
        self.stop()


class ADGSuggestionModal(discord.ui.Modal, title='Provide suggestion detail'):
    suggestion_title: discord.ui.TextInput[ADGSuggestionView] = discord.ui.TextInput(
        label='What is the title of this suggestion?',
        style=discord.TextStyle.short,
        placeholder='Make it short but related to the suggestion',
        required=True,
    )
    suggestion_description: discord.ui.TextInput[ADGSuggestionView] = discord.ui.TextInput(
        label='What is the suggestion?',
        style=discord.TextStyle.paragraph,
        placeholder='Write whatever you want as long as its related',
        max_length=2000,
        required=True,
    )

    def __init__(self, *, view: ADGSuggestionView) -> None:
        self.view = view
        self.suggestion_title.default = self.view.suggestion_data['title']
        self.suggestion_description.default = self.view.suggestion_data['description']
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction[Mafuyu]) -> None:
        sug_title = self.suggestion_title.value
        sug_description = self.suggestion_description.value

        self.view.suggestion_data['title'] = sug_title
        self.view.suggestion_data['description'] = sug_description

        e = self.view.embed()
        self.view.update_display()
        await interaction.response.edit_message(embed=e, view=self.view)


class ADGSuggestions(MafuCog):
    @commands.command(name='suggest', hidden=True)
    async def suggest(self, ctx: MafuContext) -> None:
        await ADGSuggestionView.start(ctx, ctx.author)
