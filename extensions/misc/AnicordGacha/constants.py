from __future__ import annotations

import datetime

import discord

ANICORD_DISCORD_BOT = 1257717266355851384

PULL_INTERVAL = datetime.timedelta(hours=6)


PULL_LINE_REGEX = r'Name: `(?P<name>.+)` Rarity: <:(?P<rarity>[a-zA-Z0-9]+):.+>.+ ID: `(?P<id>[0-9]+)`'


RARITY_EMOJIS = {
    1: discord.PartialEmoji(id=1259718293410021446, name='RedStar'),
    2: discord.PartialEmoji(id=1259690032554577930, name='GreenStar'),
    3: discord.PartialEmoji(id=1259557039441711149, name='YellowStar'),
    4: discord.PartialEmoji(id=1259718164862996573, name='PurpleStar'),
    5: discord.PartialEmoji(id=1259557105220976772, name='RainbowStar'),
    6: discord.PartialEmoji(id=1259689874961862688, name='BlackStar'),
}


HOLLOW_STAR = discord.PartialEmoji(name='HollowStar', id=1259556949867888660)
