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

BASE_COLOUR = discord.Colour.from_str('#FFB3DE')
ERROR_COLOUR = discord.Colour.from_str('#bb6688')

CHAR_LIMIT = 2000


class BotEmojis:
    GREY_TICK = discord.PartialEmoji(name='greyTick', id=1431312403085267066)
    GREEN_TICK = discord.PartialEmoji(name='greenTick', id=1431312422613815346)
    RED_CROSS = discord.PartialEmoji(name='redTick', id=1431312495402025010)

    PASS = discord.PartialEmoji(name='pass', id=1431313574550179944)
    SMASH = discord.PartialEmoji(name='smash', id=1431313312682999878)

    ON_SWITCH = discord.PartialEmoji(name='switch_on', id=1431313973365571656)
    OFF_SWITCH = discord.PartialEmoji(name='switch_off', id=1431313986904785061)

    CYRENE1 = discord.PartialEmoji(name='Cyrene1', id=1431550613413560440)
