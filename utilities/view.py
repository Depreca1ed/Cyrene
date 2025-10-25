from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Self

import discord

from utilities.constants import BotEmojis
from utilities.embed import Embed
from utilities.functions import fmt_str

if TYPE_CHECKING:
    from collections.abc import Iterable

    from utilities.bases.bot import Cyrene
    from utilities.bases.context import CyContext

__all__ = ('BaseView', 'PermissionView')


class BaseView(discord.ui.View):
    message: discord.Message | None

    def __init__(self, *, timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)

    async def on_timeout(self) -> None:
        with contextlib.suppress(discord.errors.NotFound):
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=None)
        self.stop()


PERMISSIONS_STRUCTURE = {
    'general': [
        'view_channels',
        'manage_channels',
        'manage_roles',
        'create_expressions',
        'manage_expressions',
        'view_audit_log',
        'view_server_insights',
        'manage_webhooks',
        'manage_server',
    ],
    'membership': [
        'create_invite',
        'change_nickname',
        'manage_nicknames',
        'kick_members',
        'ban_members',
        'moderate_members',
    ],
    'text': [
        'send_messsages',
        'send_messages_in_threads',
        'create_public_threads',
        'create_private_threads',
        'embed_links',
        'attach_files',
        'add_reactions',
        'use_external_emojis',
        'use_external_stickers',
        'use_external_sounds',
        'mention_everyone',
        'manage_messages',
        'manage_threads',
        'read_message_history',
        'send_tts',
        'send_voice_messages',
        'create_polls',
    ],
    'voice': [
        'connect',
        'speak',
        'video',
        'use_soundboard',
        'use_external_sounds',
        'use_voice_activity',
        'priority_speaking',
        'mute_memebrs',
        'deafen_members',
        'move_members',
        'set_voice_channel_status',
    ],
    'apps': [
        'use_application_commands',
        'use_activities',
        'use_external_apps',
    ],
    'events': [
        'create_events',
        'manage_events',
    ],
    'misc': [
        'request_to_speak',
        'administrator',
    ],
}


def get_permission_emoji(
    *, permissions: Iterable[bool] | None = None, permission: bool | None = None
) -> discord.PartialEmoji:
    if permissions:
        if all_true_or_false(permissions) is True:
            return BotEmojis.GREEN_TICK
        if all_true_or_false(permissions) is False:
            return BotEmojis.RED_CROSS
        return BotEmojis.GREY_TICK
    return BotEmojis.GREEN_TICK if permission and permission is True else BotEmojis.RED_CROSS


def all_true_or_false(targets: Iterable[bool]) -> None | bool:
    if all(targets):
        return True
    if not [_ for _ in targets if _ is True]:
        return False
    return None


def p_string(p: str) -> str:
    return f' **|** `{p.replace("_", " ").title()}`'


class PermissionView(BaseView):
    def __init__(
        self, ctx: CyContext, *, target: discord.Member | discord.Role | None = None, permissions: discord.Permissions
    ) -> None:
        self.ctx = ctx
        self.target = target
        self.permissions = permissions

        super().__init__()

    @discord.ui.button(label='Permissions', emoji='\U0001f6e1', style=discord.ButtonStyle.grey)
    async def permission_button(self, interaction: discord.Interaction[Cyrene], _: discord.ui.Button[Self]) -> None:
        embed = Embed(title=f'Permissions for {self.target}' if self.target else None)

        permissions = list(self.permissions)

        for p, perms in PERMISSIONS_STRUCTURE.items():
            current = [_ for _ in permissions if _[0] in perms]
            current_bools = [_[1] for _ in current]

            are_all_bool = all_true_or_false(current_bools)

            sn = 'all' if are_all_bool is True else 'no'

            entity = (
                (
                    'You',
                    'have',
                )
                if isinstance(self.target, discord.Member) and self.target.id == interaction.user.id
                else (
                    str(self.target),
                    'has',
                )
            )

            embed.add_field(
                name=str(get_permission_emoji(permissions=current_bools)) + p_string(p) + ' Permissions',
                value=fmt_str(
                    ['> ' + str(get_permission_emoji(permission=perm[1])) + p_string(perm[0]) for perm in current],
                    seperator='\n',
                )
                if are_all_bool is None
                else f'> -# **{entity[0]}** {entity[1]} {sn} permissions from the **{p.title()}** category.',
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
