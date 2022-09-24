from re import compile, match
from inspect import ismethod

import emoji
from discord import app_commands, Interaction, Emoji, Color
from discord.app_commands import Transformer, Transform, AppCommandError
from discord.utils import get

__all__ = ('EmoteTransform', 'InvalidEmote', 'ColorTransform', 'InvalidColor', 'EmoteOrDescriptionTransform')


class InvalidEmote(AppCommandError):
    pass


class EmoteTransformer(Transformer):
    _ID_REGEX = compile(r'([0-9]{15,20})$')

    async def transform(self, interaction: Interaction, value: str) -> Emoji | str:
        # Taken from discord.ext.commands.EmojiConverter

        if emoji.is_emoji(value):
            return value

        match_result = self._ID_REGEX.match(value) or match(r'<a?:[a-zA-Z0-9\_]{1,32}:([0-9]{15,20})>$', value)
        result = None
        bot = interaction.client
        guild = interaction.guild

        if match_result is None:
            # Try to get the emoji by name. Try local guild first.
            if guild:
                result = get(guild.emojis, name=value)

            if result is None:
                result = get(bot.emojis, name=value)
        else:
            emoji_id = int(match_result.group(1))

            # Try to look up emoji by id.
            result = bot.get_emoji(emoji_id)

        if result is None:
            raise InvalidEmote

        return result


EmoteTransform = Transform[Emoji | str, EmoteTransformer]


class InvalidColor(app_commands.AppCommandError):
    pass


class ColorTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str) -> Color:
        # Taken from discord.ext.commands.ColorConverter

        try:
            return Color.from_str(value)
        except ValueError:
            arg = value.lower().replace(' ', '_')
            method = getattr(Color, arg, None)
            if arg.startswith('from_') or method is None or not ismethod(method):
                raise InvalidColor
            return method()


ColorTransform = Transform[Color, ColorTransformer]


class EmoteOrDescriptionTransformer(Transformer):
    _ID_REGEX = compile(r'([0-9]{15,20})$')

    async def transform(self, interaction: Interaction, value: str) -> Emoji | str:
        # Taken from discord.ext.commands.EmojiConverter

        if emoji.is_emoji(value):
            return value

        match_result = self._ID_REGEX.match(value) or match(r'<a?:[a-zA-Z0-9\_]{1,32}:([0-9]{15,20})>$', value)
        result = None
        bot = interaction.client
        guild = interaction.guild

        if match_result is None:
            # Try to get the emoji by name. Try local guild first.
            if guild:
                result = get(guild.emojis, name=value)

            if result is None:
                result = get(bot.emojis, name=value)
        else:
            emoji_id = int(match_result.group(1))

            # Try to look up emoji by id.
            result = bot.get_emoji(emoji_id)

        return result or value


EmoteOrDescriptionTransform = Transform[Emoji | str, EmoteOrDescriptionTransformer]
