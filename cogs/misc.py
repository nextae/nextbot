from contextlib import redirect_stdout
from io import StringIO
from random import choice
from random import randrange
from textwrap import indent
from typing import TYPE_CHECKING, Literal

import discord
from discord import app_commands, Interaction, Member
from discord.app_commands import command, Range
from discord.ext.commands import Context, Cog, command as normal_command

from utils.checks import is_next
from utils.embeds import *

if TYPE_CHECKING:
    from nextbot import NextBot

Base = Range[int, 2, 35]


class Misc(Cog):
    bot: 'NextBot'

    def __init__(self, bot: 'NextBot'):
        self.bot = bot

        # Add the context menus
        iq_context_menu = app_commands.ContextMenu(name='Show IQ', callback=self.iq)
        self.bot.tree.add_command(iq_context_menu)

        pp_size_context_menu = app_commands.ContextMenu(name='Show PP Size', callback=self.pp_size)
        self.bot.tree.add_command(pp_size_context_menu)

        describe_context_menu = app_commands.ContextMenu(name='Describe', callback=self.describe)
        self.bot.tree.add_command(describe_context_menu)

    @staticmethod
    async def iq(interaction: Interaction, member: Member):
        """Shows member's IQ."""

        await green_embed(interaction, f'{member.mention}\'s IQ is {randrange(20, 201)}')

    @staticmethod
    async def pp_size(interaction: Interaction, member: Member):
        """Shows member's PP size."""

        pp = f'8{"=" * randrange(1, 16)}D'

        await green_embed(interaction, f'{member.mention}\'s PP:\n{pp}')

    @staticmethod
    async def describe(interaction: Interaction, member: Member):
        """Shows a random response about the member."""

        responses = (
            'pepega',
            'a retard',
            'a nice guy',
            'dumb',
            'stupid',
            'retarded',
            'a Spellbreak gamer',
            'a mongoloid',
            'a noob',
            'a 5Head',
            'a gaming warlord',
            'a TFT player',
            'a nekker slayer',
            'a juicer',
            'a GIGACHAD',
            'british OMEGALUL',
            'brain damaged',
            'mentally damaged'
        )

        await green_embed(interaction, f'{member.mention} is {choice(responses)}')

    @command()
    @app_commands.describe(a='The first number', sign='The sign to use', b='The second number')
    async def math(self, interaction: Interaction, a: float, sign: Literal['+', '-', '*', '/'], b: float):
        """Calculates basic equations."""

        if a.is_integer():
            a = round(a)
        if b.is_integer():
            b = round(b)

        result = 0
        if sign == '+':
            result = a + b
        elif sign == '-':
            result = a - b
        elif sign == '*':
            result = a * b
        elif sign == '/':
            result = a / b

        await green_embed(interaction, f'{a} {sign} {b} = {round(result, 6)}')

    @command(name='numbersystemconverter')
    @app_commands.describe(
        input_base='The base to convert from',
        output_base='The base to convert to',
        number='The number to convert'
    )
    async def number_system_converter(self, interaction: Interaction, input_base: Base, output_base: Base, number: str):
        """Converts a number from input_base to output_base."""

        signs = '0123456789ABCDEFGHJKLMNOPQRSTUVWXYZ'
        number = number.upper()
        array = []
        for sign in number:
            array.append(signs.index(sign))

        decimal = array[0]
        for i in range(1, len(number)):  # converting from input_base to decimal
            decimal = decimal * input_base + array[i]

        result = ''
        while decimal > 0:  # converting from decimal to output_base
            result = signs[decimal % output_base] + result
            decimal //= output_base

        await green_embed(interaction, f'{number} in base {input_base} = **{result}** in base {output_base}')

    @normal_command(name='setmessage', aliases=['setmsg'])
    @is_next()
    async def set_message(self, ctx: Context, *, message: str = 'nextbot | /help'):
        """Sets a custom presence message."""

        await self.bot.change_presence(activity=discord.Game(message))

    @normal_command(aliases=['eval'])
    @is_next()
    async def evaluate(self, ctx: Context, *, body: str):
        """Evaluates a code snippet."""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'discord': discord
        }

        body = body.strip('` ')
        if body.startswith('py'):
            body = body[2:]

        stdout = StringIO()

        to_compile = f'async def func():\n{indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        value = stdout.getvalue()

        if value:
            await ctx.send(f'```py\n{value}\n```')
        if ret is not None:
            await ctx.send(f'Value returned:```py\n{ret}\n```')

    @normal_command()
    @is_next()
    async def load(self, ctx: Context, name: str):
        """Loads an extension."""

        await self.bot.load_extension(f'cogs.{name}')

    @normal_command()
    @is_next()
    async def unload(self, ctx: Context, name: str):
        """Unloads an extension."""

        await self.bot.unload_extension(f'cogs.{name}')

    @normal_command()
    @is_next()
    async def reload(self, ctx: Context, name: str):
        """Reloads an extension."""

        await self.bot.reload_extension(f'cogs.{name}')


async def setup(bot: 'NextBot'):
    await bot.add_cog(Misc(bot))
