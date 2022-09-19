from logging import getLogger

from discord import Interaction
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from utils.embeds import error_embed

log = getLogger(__name__)

__all__ = ('error_handler', 'interactions_error_handler')


async def error_handler(ctx: commands.Context, error: commands.CommandError):
    """Custom error handler."""

    if isinstance(error, commands.MemberNotFound):
        return await error_embed(ctx, f'User {error.argument} not found!')

    if isinstance(error, commands.ChannelNotFound):
        return await error_embed(ctx, f'Channel {error.argument} not found!')

    if isinstance(error, commands.RoleNotFound):
        return await error_embed(ctx, f'Role {error.argument} not found!')

    if isinstance(error, commands.MessageNotFound):
        return await error_embed(ctx, f'Message {error.argument} not found!')

    if isinstance(error, commands.MissingRole):
        return await error_embed(ctx, f'You need to have the `{error.missing_role}` role to run this command.')

    if isinstance(error, commands.MissingRequiredArgument):
        return await error_embed(ctx, f'`{error.param.name}` is a required argument that is missing.')

    if isinstance(error, (commands.MissingPermissions, commands.CheckFailure)):
        return await error_embed(ctx, 'You don\'t have permission to use this command.')

    if ctx.guild is not None:
        error_channel = get(ctx.guild.text_channels, name='bot-errors')

        if error_channel is not None:
            await error_embed(error_channel, str(error), None)

    log.error(error)
    raise error


async def interactions_error_handler(interaction: Interaction, error: app_commands.AppCommandError):
    """Custom error handler for interactions."""

    if isinstance(error, app_commands.MissingRole):
        return await error_embed(interaction, f'You need to have the `{error.missing_role}` role to run this command.')

    if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        return await error_embed(interaction, 'You don\'t have permission to use this command.')

    if interaction.guild is not None:
        error_channel = get(interaction.guild.text_channels, name='bot-errors')

        if error_channel is not None:
            await error_embed(error_channel, str(error), None)

    log.error(error)
    raise error
