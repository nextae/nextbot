from typing import TYPE_CHECKING, Literal

import discord
import emoji
from discord import app_commands, Interaction, Message, Emoji, Color
from discord.app_commands import command, Range
from discord.ext.commands import GroupCog
from motor.motor_asyncio import AsyncIOMotorCollection

from utils.embeds import error_embed, success_embed, green_embed, Embed
from utils.errors import interactions_error_handler
from utils.transformers import EmoteTransform, ColorTransform, EmoteOrDescriptionTransform, InvalidEmote, InvalidColor
from utils.views import YesNoView, RolesView

if TYPE_CHECKING:
    from nextbot import NextBot


class Roles(GroupCog, name='roles'):
    bot: 'NextBot'
    roles: AsyncIOMotorCollection

    def __init__(self, bot: 'NextBot'):
        self.bot = bot
        self.roles = self.bot.db['roles']

    async def cog_load(self):
        """Adds the Roles view."""

        self.bot.add_view(RolesView(self.bot))

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Handles the errors."""

        if hasattr(interaction.command, 'on_error'):
            return

        await interactions_error_handler(interaction, error)

    async def update_select_menu(self, select_message: Message, roles_entry: dict):
        """Adds a role to the Roles selection menu."""

        await select_message.edit(view=RolesView(self.bot, roles_entry.get('roles')))

    @staticmethod
    async def get_select_menu_message(guild: discord.Guild, roles_entry: dict) -> Message | None:
        """Gets the Roles selection menu Message."""

        channel = guild.get_channel(roles_entry['channel_id'])
        try:
            return await channel.fetch_message(roles_entry['message_id'])
        except discord.NotFound:
            return None

    @GroupCog.listener('on_guild_role_delete')
    async def detect_removed_roles(self, role: discord.Role):
        """Detects when a role gets removed and removes it from the Roles selection as well."""

        guild = role.guild

        roles_entry = await self.roles.find_one({'guild_id': guild.id})
        if roles_entry is None:
            return

        entry_to_remove = None
        for role_entry in roles_entry['roles']:
            if role_entry['role_id'] == role.id:
                entry_to_remove = role_entry
                break

        if entry_to_remove is None:
            return

        select_message = await self.get_select_menu_message(guild, roles_entry)
        if select_message is None:
            return

        await self.roles.update_one({'guild_id': guild.id}, {'$pull': {'roles': entry_to_remove}})

        roles_entry['roles'].remove(entry_to_remove)

        await self.update_select_menu(select_message, roles_entry)

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(
        channel='The channel to setup Roles selection in',
    )
    async def setup(self, interaction: Interaction, channel: discord.TextChannel):
        """Sets up the Roles selection."""

        if await self.roles.find_one({'guild_id': interaction.guild_id}):
            return await error_embed(
                interaction,
                'Roles selection is already setup in this server.\n'
                'Use the `/roles reset` command if you want to start over'
            )

        embed = Embed(
            title='Roles selection',
            description='Use the selection menus below to choose which roles you want to receive or lose'
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        message = await channel.send(embed=embed, view=RolesView(self.bot, first_setup=True))

        roles_entry = {
            'guild_id': interaction.guild.id,
            'channel_id': channel.id,
            'message_id': message.id,
            'roles': []
        }

        await self.roles.insert_one(roles_entry)

        await success_embed(
            interaction, 'Successfully setup the roles selection! You can now add roles with the `/roles add` command'
        )

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(
        role='The role you want to add to the roles selection. '
             'You can leave it empty and fill the name and color arguments to create a new role instead',
        emote='Optional, The emote that will show in the Select menu',
        description='Optional, the description that will show in the Select menu',
        name='The name of the new role that will be created if you don\'t use the role argument',
        color='The color of the new role that will be created if you don\'t use the role argument'
    )
    async def add(
            self,
            interaction: Interaction,
            role: discord.Role = None,
            emote: EmoteTransform = None,
            description: Range[str, 0, 100] = None,
            name: Range[str, 0, 100] = None,
            color: ColorTransform = None
    ):
        """Adds a role to the Roles selection.
        You can either use an existing role in the role argument
        or leave it empty and fill the name and color arguments to create a new role"""

        await interaction.response.defer()

        roles_entry = await self.roles.find_one({'guild_id': interaction.guild_id})
        if roles_entry is None:
            return await error_embed(
                interaction, 'You need to setup roles selection first using the `/roles setup` command!'
            )

        if role is not None and (name or color):
            return await error_embed(
                interaction,
                'You can\'t use the `role` argument together with the `name` and/or `color` arguments!'
            )

        if role is None and name is None:
            return await error_embed(interaction, 'You need to use either the `role` or `name` argument!')

        embed = discord.Embed(
            description=f'**Name**: {role.name if role else name}\n'
                        f'**Description**:** {description}\n'
                        f'**Emote**: {emote}\n\n'
                        f'**Add the role?**',
            color=role.color if role else color
        )
        view = YesNoView(interaction.user.id)
        channel = interaction.channel
        confirmation_message = await channel.send(embed=embed, view=view)

        await view.wait()

        if view.value is None:
            await view.disable_buttons(confirmation_message)

            return await error_embed(interaction, f'{interaction.user.mention} you took too long to answer!')

        if not view.value:
            return await error_embed(interaction, 'Successfully cancelled adding the role!')

        select_message = await self.get_select_menu_message(interaction.guild, roles_entry)
        if select_message is None:
            return await error_embed(interaction, 'Couldn\'t find the roles selection menu message!')

        if role is None:
            try:
                role = await interaction.guild.create_role(name=name, color=color or Color.default(), mentionable=True)
            except discord.Forbidden:
                return await error_embed(interaction, 'I don\'t have permissions to create the role!')

        role_entry = {
            'role_id': role.id,
            'emote': emote.id if isinstance(emote, Emoji) else emote,
            'name': role.name,
            'description': description
        }

        await self.roles.update_one({'guild_id': interaction.guild_id}, {'$push': {'roles': role_entry}})

        roles_entry['roles'].append(role_entry)

        await self.update_select_menu(select_message, roles_entry)

        await success_embed(interaction, 'Successfully added the role!')

    @add.error
    async def add_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Handles the errors for the /roles add command."""

        if isinstance(error, InvalidEmote):
            return await error_embed(interaction, 'Invalid emote or the bot cannot use this emote!')

        if isinstance(error, InvalidColor):
            return await error_embed(interaction, 'Invalid color!')

        await interactions_error_handler(interaction, error)

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(
        role='The role you want to edit the emote or description for',
        what_to_edit='Choose either Emote or Description',
        new_value='New value of the Emote or Description',
    )
    async def edit(
            self,
            interaction: Interaction,
            role: discord.Role,
            what_to_edit: Literal['Emote', 'Description'],
            new_value: EmoteOrDescriptionTransform
    ):
        """Edits the Emote or Description of a role in the Roles selection."""

        roles_entry = await self.roles.find_one({'guild_id': interaction.guild_id})
        if roles_entry is None:
            return await error_embed(
                interaction, 'You need to setup roles selection first using the `/roles setup` command!'
            )

        if what_to_edit == 'Emote' and not isinstance(new_value, Emoji) and not emoji.is_emoji(new_value):
            return await error_embed(interaction, 'Invalid emote or the bot cannot use this emote!')

        entry_index = None
        for index, role_entry in enumerate(roles_entry['roles']):
            if role_entry['role_id'] == role.id:
                if what_to_edit == 'Emote':
                    role_entry['emote'] = new_value.id if isinstance(new_value, Emoji) else new_value
                else:
                    role_entry['description'] = new_value

                entry_index = index
                break

        if entry_index is None:
            return await error_embed(interaction, 'This role is not a part of the roles to select!')

        select_message = await self.get_select_menu_message(interaction.guild, roles_entry)
        if select_message is None:
            return await error_embed(interaction, 'Couldn\'t find the roles selection menu message!')

        set_query = {
            f'roles.{entry_index}.{what_to_edit.lower()}': new_value.id if isinstance(new_value, Emoji) else new_value
        }
        await self.roles.update_one({'guild_id': interaction.guild_id}, {'$set': set_query})

        await self.update_select_menu(select_message, roles_entry)

        await success_embed(interaction, f'Successfully edited the role {what_to_edit.lower()}!')

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(
        role='The role to remove from Roles selection',
        remove_from_server='Whether to remove the role from the server too, or just from the Roles selection'
    )
    async def remove(self, interaction: Interaction, role: discord.Role, remove_from_server: bool = None):
        """Removes a role from the Roles selection."""

        roles_entry = await self.roles.find_one({'guild_id': interaction.guild_id})
        if roles_entry is None:
            return await error_embed(
                interaction, 'You need to setup roles selection first using the `/roles setup` command!'
            )

        entry_to_remove = None
        for role_entry in roles_entry['roles']:
            if role_entry['role_id'] == role.id:
                entry_to_remove = role_entry
                break

        if entry_to_remove is None:
            return await error_embed(interaction, 'This role is not a part of the roles to select!')

        select_message = await self.get_select_menu_message(interaction.guild, roles_entry)
        if select_message is None:
            return await error_embed(interaction, 'Couldn\'t find the roles selection menu message!')

        await self.roles.update_one({'guild_id': interaction.guild_id}, {'$pull': {'roles': entry_to_remove}})

        roles_entry['roles'].remove(entry_to_remove)

        await self.update_select_menu(select_message, roles_entry)

        if remove_from_server:
            try:
                await role.delete()
            except discord.Forbidden:
                return await error_embed(interaction, 'I did not have permissions to remove the role from the server!')

        await success_embed(interaction, 'Successfully removed the role!')

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def reset(self, interaction: Interaction):
        """Resets the Roles selection."""

        roles_entry = await self.roles.find_one({'guild_id': interaction.guild_id})
        if roles_entry is None:
            return await error_embed(
                interaction, 'You need to setup roles selection first using the `/roles setup` command!'
            )

        view = YesNoView(interaction.user.id)
        await green_embed(interaction, '**Are you sure?**', view=view)

        await view.wait()

        if view.value is None:
            return await error_embed(interaction, f'{interaction.user.mention} you took too long to answer!')

        if not view.value:
            return

        select_message = await self.get_select_menu_message(interaction.guild, roles_entry)
        if select_message is None:
            return await error_embed(interaction, 'Couldn\'t find the roles selection menu message!')

        try:
            await select_message.delete()
        except (discord.Forbidden, discord.HTTPException):
            return await error_embed(interaction, 'Removing the role selection menu message failed!')

        await self.roles.delete_one({'guild_id': interaction.guild_id})

        await success_embed(interaction, 'Successfully reset the roles selection!')


async def setup(bot: 'NextBot'):
    await bot.add_cog(Roles(bot))
