from __future__ import annotations

import discord

__ALL__ = (
    'BASE_COLOUR',
    'ERROR_COLOUR',
    'BOT_THRESHOLD',
    'BLACKLIST_COLOUR',
    'BOT_FARM_COLOUR',
    'BotEmojis',
    'WebhookThreads',
)

BASE_COLOUR = discord.Colour.from_str('#A27869')
ERROR_COLOUR = discord.Colour.from_str('#bb6688')

CHAR_LIMIT = 2000


class BotEmojis:
    GREY_TICK = discord.PartialEmoji(name='grey_tick', id=1278414780427796631)
    GREEN_TICK = discord.PartialEmoji(name='greentick', id=1297976474141200529, animated=True)
    RED_CROSS = discord.PartialEmoji(name='redcross', id=1315758805585498203, animated=True)
    STATUS_ONLINE = discord.PartialEmoji(name='status_online', id=1328344385783468032)
    PASS = discord.PartialEmoji(name='PASS', id=1339697021942108250)
    SMASH = discord.PartialEmoji(name='SMASH', id=1339697033589559296)
    SLASH = discord.PartialEmoji(name='Slash_command_white', id=1352388308046581880)
