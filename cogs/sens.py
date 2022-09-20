from typing import TYPE_CHECKING, Literal

from discord import app_commands, Interaction
from discord.app_commands import command, Range
from discord.ext.commands import Cog

from utils.embeds import green_embed

if TYPE_CHECKING:
    from nextbot import NextBot


Game = Literal['Overwatch', 'Spellbreak', 'Apex', 'Valorant']


class Sens(Cog):
    bot: 'NextBot'
    values: dict[str, float] = {
        'overwatch': 0.00000721784,
        'spellbreak': 0.00087480216,
        'apex': 0.00002405945,
        'valorant': 0.00007653094
    }

    def __init__(self, bot: 'NextBot'):
        self.bot = bot

    def get_value(self, game: str) -> float:
        """Gets the value for a game."""

        return self.values.get(game.lower())

    @command()
    @app_commands.describe(
        game='The game to calculate cm / 360',
        sens='The sensitivity in the given game',
        dpi='The DPI used'
    )
    async def sensitivity(self, interaction: Interaction, game: Game, sens: Range[float, 0], dpi: Range[int, 0]):
        """Calculates cm / 360 for given sens and dpi."""

        cm = 1 / (sens * dpi * self.get_value(game))

        await green_embed(interaction, f'Your cm / 360° is: **{round(cm, 6)}**')

    @command()
    @app_commands.describe(
        game1='The game to convert the sensitivity from',
        game2='The game to convert the sensitivity to',
        sens='The sensitivity in game1'
    )
    async def convert(self, interaction: Interaction, game1: Game, game2: Game, sens: Range[float, 0]):
        """Converts a sensitivity from game1 to game2."""

        game1_cm = 1 / (sens * self.get_value(game1))
        game2_sens = 1 / game1_cm / self.get_value(game2)

        await green_embed(interaction, f'Your sensitivity in **{game2}** is: **{round(game2_sens, 4)}**')


async def setup(bot: 'NextBot'):
    await bot.add_cog(Sens(bot))
