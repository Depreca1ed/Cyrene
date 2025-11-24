from __future__ import annotations

import discord

ANICORD_DISCORD_BOT = 1257717266355851384
ANICORD_GACHA_SERVER = 1242232552845086782

PULLALL_LINE_REGEX = r'Name: `(?P<name>.+)` Rarity: <:(?P<rarity>[a-zA-Z0-9]+):.+>.+ ID: `(?P<id>[0-9]+)`*'

SINGLE_PULL_REGEX = r"""Rarity: <:(?P<rarity>[a-zA-Z0-9]+):.+>
Burn Worth: (?P<burn_worth>[0-9]+)
ID: (?P<id>[0-9]+)"""

WEEKLY_PULL_REGEX = r"""\#\# (?P<name>.+)

\*\*Theme:\*\* (?P<theme>.+)
\*\*ID:\*\* `(?P<id>[0-9]+)`

\*\*Rarity:\*\* <:(?P<rarity>[a-zA-Z0-9]+):.+>
\*\*Burn Worth:\*\* (?P<burn_worth>[0-9]+)"""

PACK_PAGE_PULL_REGEX = r"""ID: `(?P<id>[0-9]+)`
Name: (?P<name>.+)
Rarity: <:(?P<rarity>[a-zA-Z0-9]+):.+>*
"""

PACK_LIST_PULL_REGEX = r'`[0-9]\.` \*\*(?P<name>.+)\*\* - <:(?P<rarity>[a-zA-Z0-9]+):.+>.+ - ID: `(?P<id>[0-9]+)`*'

RARITY_EMOJIS = {
    1: discord.PartialEmoji(id=1259718293410021446, name='RedStar'),
    2: discord.PartialEmoji(id=1259690032554577930, name='GreenStar'),
    3: discord.PartialEmoji(id=1259557039441711149, name='YellowStar'),
    4: discord.PartialEmoji(id=1259718164862996573, name='PurpleStar'),
    5: discord.PartialEmoji(id=1259557105220976772, name='RainbowStar'),
    6: discord.PartialEmoji(id=1259689874961862688, name='BlackStar'),
}
