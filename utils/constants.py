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

BASE_COLOUR = discord.Colour.from_str('#4B506F')
ERROR_COLOUR = discord.Colour.from_str('#bb6688')

BOT_THRESHOLD = 80
BLACKLIST_COLOUR = discord.Colour.from_str('#ccaa88')
BOT_FARM_COLOUR = discord.Colour.from_str('#fff5e8')

CHAR_LIMIT = 2000


class BotEmojis:
    GREY_TICK = discord.PartialEmoji(name='grey_tick', id=1278414780427796631)
    GREEN_TICK = discord.PartialEmoji(name='greentick', id=1297976474141200529, animated=True)
    RED_CROSS = discord.PartialEmoji(name='redcross', id=1315758805585498203, animated=True)
    STATUS_ONLINE = discord.PartialEmoji(name='status_online', id=1328344385783468032)
    PASS = discord.PartialEmoji(name='PASS', id=1339697021942108250)
    SMASH = discord.PartialEmoji(name='SMASH', id=1339697033589559296)
