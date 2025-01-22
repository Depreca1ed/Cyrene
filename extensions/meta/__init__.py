from __future__ import annotations

import colorsys
from io import BytesIO
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from jishaku.functools import executor_function
from PIL import Image

from utils import Context, Embed, better_string

from .botinfo import BotInformation
from .serverinfo import ServerInfo
from .userinfo import Userinfo

if TYPE_CHECKING:
    from bot import Mafuyu

THUMBNAIL_SIZE = (128, 128)


@executor_function
def make_image(colour: discord.Colour) -> BytesIO:
    thumbnail = Image.new('RGB', THUMBNAIL_SIZE, color=colour.to_rgb())
    buffer = BytesIO()
    thumbnail.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer


class Meta(BotInformation, Userinfo, ServerInfo, name='Meta'):
    """For everything related to Discord or Mafuyu."""

    @commands.hybrid_command(name='colour', aliases=['color'], description='Get information about a certain colour')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def colour(self, ctx: Context, *, colour: discord.Colour | None = None) -> None:
        colour = colour or discord.Colour.random()

        rgb = colour.to_rgb()

        def rounder(v: tuple[float, float, float]) -> tuple[int, int, int]:
            return round(v[0]), round(v[1]), round(v[2])

        embed = Embed(
            title=str(colour).upper(),
            description=better_string(
                (
                    f'- **RGB :** `{rounder(rgb)}`',
                    f'- **INT :** `{(int(colour))}`',
                    f'- **HSV :** `{rounder(colorsys.rgb_to_hsv(*rgb))}`',
                    f'- **HLS :** `{rounder(colorsys.rgb_to_hls(*rgb))}`',
                    f'- **YIQ :** `{rounder(colorsys.rgb_to_yiq(*rgb))}`',
                ),
                seperator='\n',
            ),
            colour=colour,
        )

        image = await make_image(colour)
        _ = discord.File(image, filename='colour.png')
        embed.set_thumbnail(url='attachment://colour.png')

        await ctx.reply(embed=embed, file=_)


async def setup(bot: Mafuyu) -> None:
    await bot.add_cog(Meta(bot))
