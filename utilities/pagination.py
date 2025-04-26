from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

import discord

from .view import BaseView

if TYPE_CHECKING:
    from discord.ext import menus

    from utilities.bases.context import MafuContext

__all__ = ('Paginator',)


class SkipToModal(discord.ui.Modal, title='Skip to page...'):
    page = discord.ui.TextInput[Self](
        label='Which page do you want to skip to?',
        max_length=10,
        placeholder='This prompt times out in 20 seconds...',
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.value = None
        self.interaction: discord.Interaction | None = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self.value = self.page.value


class Paginator(BaseView):
    # This Source Code Form is subject to the terms of the Mozilla Public
    # License, v. 2.0. If a copy of the MPL was not distributed with this
    # file, You can obtain one at http://mozilla.org/MPL/2.0/.
    #
    # Modified version of the RoboPages class, from R. Danny, source/credits:
    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/paginator.py

    def __init__(
        self,
        source: menus.PageSource,
        *,
        ctx: MafuContext,
        check_embeds: bool = True,
        compact: bool = False,
    ) -> None:
        super().__init__()
        self.current_modal: SkipToModal | None = None
        self.source: menus.PageSource = source
        self.check_embeds: bool = check_embeds
        self.ctx: MafuContext = ctx
        self.message: discord.Message | None = None
        self.current_page: int = 0
        self.compact: bool = compact
        self.clear_items()
        self.fill_items()

    def fill_items(self) -> None:
        if self.source.is_paginating():
            max_pages = self.source.get_max_pages()
            use_last_and_first = max_pages is not None and max_pages >= 2
            if use_last_and_first:
                self.add_item(self.go_to_first_page)
            self.add_item(self.go_to_previous_page)
            if not self.compact:
                self.add_item(self.go_to_current_page)
            self.add_item(self.go_to_next_page)
            if use_last_and_first:
                self.add_item(self.go_to_last_page)

    async def _get_kwargs_from_page(self, page: int) -> dict[str, Any]:
        value: str | discord.Embed | Any = await discord.utils.maybe_coroutine(self.source.format_page, self, page)  # pyright: ignore[reportUnknownMemberType]

        if isinstance(value, str):
            return {'content': value, 'embed': None}
        if isinstance(value, discord.Embed):
            return {'embed': value, 'content': None}
        return {}

    async def show_page(self, interaction: discord.Interaction, page_number: int) -> None:
        page: Any = await self.source.get_page(page_number)  # pyright: ignore[reportUnknownMemberType]

        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(page_number)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    def _update_labels(self, page_number: int) -> None:
        self.go_to_first_page.disabled = page_number == 0
        if self.compact:
            max_pages = self.source.get_max_pages()
            self.go_to_last_page.disabled = max_pages is None or (page_number + 1) >= max_pages
            self.go_to_next_page.disabled = max_pages is not None and (page_number + 1) >= max_pages
            self.go_to_previous_page.disabled = page_number == 0
            return

        self.go_to_current_page.label = str(page_number + 1)
        self.go_to_previous_page.label = str(page_number)
        self.go_to_next_page.label = str(page_number + 2)
        self.go_to_next_page.disabled = False
        self.go_to_previous_page.disabled = False
        self.go_to_first_page.disabled = False

        max_pages = self.source.get_max_pages()
        if max_pages is not None:
            self.go_to_last_page.disabled = (page_number + 1) >= max_pages
            if (page_number + 1) >= max_pages:
                self.go_to_next_page.disabled = True
                self.go_to_next_page.label = '…'
            if page_number == 0:
                self.go_to_previous_page.disabled = True
                self.go_to_previous_page.label = '…'

    async def show_checked_page(self, interaction: discord.Interaction, page_number: int) -> None:
        max_pages = self.source.get_max_pages()
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction, page_number)
            elif max_pages > page_number >= 0:
                await self.show_page(interaction, page_number)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message('This pagination menu cannot be controlled by you, sorry!', ephemeral=True)
        return False

    async def start(self, *, ephemeral: bool = False, message: discord.Message | None = None) -> None:
        await self.source.prepare()
        page: Any = await self.source.get_page(0)  # pyright: ignore[reportUnknownMemberType]
        kwargs = await self._get_kwargs_from_page(page)

        self._update_labels(0)

        if message is None:
            self.message = await self.ctx.send(**kwargs, view=self, ephemeral=ephemeral)
            return

        self.message = await message.edit(**kwargs, view=self)

    @discord.ui.button(label='≪', style=discord.ButtonStyle.grey)
    async def go_to_first_page(self, interaction: discord.Interaction, _: discord.ui.Button[Self]) -> None:
        """Go to the first page."""
        await self.show_page(interaction, 0)

    @discord.ui.button(label='Back', style=discord.ButtonStyle.blurple)
    async def go_to_previous_page(self, interaction: discord.Interaction, _: discord.ui.Button[Self]) -> None:
        """Go to the previous page."""
        await self.show_checked_page(interaction, self.current_page - 1)

    @discord.ui.button(label='Current', style=discord.ButtonStyle.grey)
    async def go_to_current_page(self, interaction: discord.Interaction, _: discord.ui.Button[Self]) -> None:
        """Lets you type a page number to go to."""
        if self.current_modal is not None and not self.current_modal.is_finished():
            self.current_modal.stop()

        self.current_modal = SkipToModal(timeout=20)
        await interaction.response.send_modal(self.current_modal)
        timed_out = await self.current_modal.wait()

        if timed_out:
            await interaction.followup.send('Took too long.', ephemeral=True)
        elif self.current_modal.interaction is None or not self.current_modal.value:
            return
        else:
            try:
                page = int(self.current_modal.value)
            except ValueError:
                await self.current_modal.interaction.response.send_message('Invalid page number.', ephemeral=True)
            else:
                await self.current_modal.interaction.response.defer()
                await self.show_checked_page(interaction, page - 1)

    @discord.ui.button(label='Next', style=discord.ButtonStyle.blurple)
    async def go_to_next_page(self, interaction: discord.Interaction, _: discord.ui.Button[Self]) -> None:
        """Go to the next page."""
        await self.show_checked_page(interaction, self.current_page + 1)

    @discord.ui.button(label='≫', style=discord.ButtonStyle.grey)
    async def go_to_last_page(self, interaction: discord.Interaction, _: discord.ui.Button[Self]) -> None:
        """Go to the last page."""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(interaction, self.source.get_max_pages() - 1)  # type: ignore  # noqa: PGH003
