from __future__ import annotations

import contextlib

import discord

__all__ = ('BaseView',)

CHAR_LIMIT = 2000


class BaseView(discord.ui.View):
    message: discord.Message | None

    async def on_timeout(self) -> None:
        with contextlib.suppress(discord.errors.NotFound):
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=None)
        self.stop()
