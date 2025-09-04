from __future__ import annotations

import datetime

import discord

ANICORD_DISCORD_BOT = 1257717266355851384

PULL_INTERVAL = datetime.timedelta(hours=6)


PULLALL_LINE_REGEX = r'Name: `(?P<name>.+)` Rarity: <:(?P<rarity>[a-zA-Z0-9]+):.+>.+ ID: `(?P<id>[0-9]+)`'

SINGLE_PULL_REGEX = r"""Rarity: <:(?P<rarity>[a-zA-Z0-9]+):.+>
Burn Worth: (?P<burn_worth>[0-9]+)
ID: (?P<id>[0-9]+)"""

RARITY_EMOJIS = {
    1: discord.PartialEmoji(id=1259718293410021446, name='RedStar'),
    2: discord.PartialEmoji(id=1259690032554577930, name='GreenStar'),
    3: discord.PartialEmoji(id=1259557039441711149, name='YellowStar'),
    4: discord.PartialEmoji(id=1259718164862996573, name='PurpleStar'),
    5: discord.PartialEmoji(id=1259557105220976772, name='RainbowStar'),
    6: discord.PartialEmoji(id=1259689874961862688, name='BlackStar'),
}


HOLLOW_STAR = discord.PartialEmoji(name='HollowStar', id=1259556949867888660)

RARITY_PULL_MESSAGES = {
    1: 'You won a Common Card',
    2: 'Nice! You won an Uncommon Card!',
    3: 'Oooo! You won a Rare Card!!',
    4: "Woah!!! You won a Super Rare Card! You're pretty lucky!",
    5: 'Holycow!!! A Legendary Card!! You hit the Jackpot!!! CONGRATS! \U0001f44f',
    6: "Wait...WHAT!?! This Card doesn't even exist in our Database, HOW DID YOU GET THIS!?",
}
