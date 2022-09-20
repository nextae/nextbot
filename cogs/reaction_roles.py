from re import search
from typing import TYPE_CHECKING

import discord
from discord import app_commands, Interaction, Message
from discord.app_commands import command
from discord.ext.commands import GroupCog
from motor.motor_asyncio import AsyncIOMotorCollection

from utils.embeds import error_embed, success_embed, green_embed, Embed
from utils.errors import interactions_error_handler
from utils.views import YesNoView

if TYPE_CHECKING:
    from nextbot import NextBot


class ReactionRoles(GroupCog, name='reactionroles'):
    bot: 'NextBot'
    guilds: AsyncIOMotorCollection
    reactions: AsyncIOMotorCollection

    def __init__(self, bot: 'NextBot'):
        self.bot = bot
        self.guilds = self.bot.db['rr_guilds']
        self.reactions = self.bot.db['rr_reactions']

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Handles the errors."""

        if hasattr(interaction.command, 'on_error'):
            return

        await interactions_error_handler(interaction, error)

    @staticmethod
    async def add_role_to_embed(embed_message: Message, name: str, reaction: str):
        """Adds a role to the ReactionRoles embed."""

        embed = embed_message.embeds[0]
        embed.add_field(name=reaction, value=name, inline=True)
        await embed_message.edit(embed=embed)
        await embed_message.add_reaction(reaction)

    @staticmethod
    async def remove_role_from_embed(embed_message: Message, name: str):
        """Removes a role from the ReactionRoles embed."""

        embed = embed_message.embeds[0]
        fields = embed.fields
        role = [x for x in fields if x.value == name][0]
        embed.remove_field(fields.index(role))
        await embed_message.edit(embed=embed)
        await embed_message.clear_reaction(role.name)

    async def get_embed_message(self, guild: discord.Guild) -> Message | None:
        """Gets the ReactionRoles embed Message."""

        guild_data = await self.guilds.find_one({'guild_id': guild.id})

        embed_channel = guild.get_channel(guild_data['channel_id'])
        try:
            return await embed_channel.fetch_message(guild_data['embed_message_id'])
        except discord.NotFound:
            return None

    @GroupCog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Detects a reaction."""

        user_id = payload.user_id
        if user_id == self.bot.user.id:
            return

        guild_id = payload.guild_id

        guild_exists = await self.guilds.find_one({'guild_id': guild_id})
        if guild_exists is None:
            return

        if guild_exists['embed_message_id'] != payload.message_id:
            return

        reaction = payload.emoji

        role = await self.reactions.find_one({'guild_id': guild_id, 'emote': str(reaction)})
        if role is None:
            return

        guild = self.bot.get_guild(guild_id)
        member = guild.get_member(user_id)
        role = guild.get_role(role['role_id'])
        await member.add_roles(role)

    @GroupCog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Detects a reaction remove."""

        user_id = payload.user_id
        if user_id == self.bot.user.id:
            return

        guild_id = payload.guild_id

        guild_exists = await self.guilds.find_one({'guild_id': guild_id})
        if guild_exists is None:
            return

        if guild_exists['embed_message_id'] != payload.message_id:
            return

        reaction = payload.emoji

        role = await self.reactions.find_one({'guild_id': guild_id, 'emote': str(reaction)})
        if role is None:
            return

        guild = self.bot.get_guild(guild_id)
        member = guild.get_member(user_id)
        role = guild.get_role(role['role_id'])
        await member.remove_roles(role)

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(
        channel='The channel to setup Reaction Roles in',
    )
    async def setup(self, interaction: Interaction, channel: discord.TextChannel):
        """Sets up ReactionRoles."""

        if await self.guilds.find_one({'guild_id': interaction.guild.id}):
            return await error_embed(
                interaction,
                'Reaction roles are already setup in this server.\n'
                'Use the `/rr reset` command if you want to start over'
            )

        embed = Embed(title='React to get your role!')
        embed.set_author(name='Reaction roles', icon_url=self.bot.user.avatar.url)
        message = await channel.send(embed=embed)

        guilds_entry = {
            'guild_id': interaction.guild.id,
            'channel_id': channel.id,
            'embed_message_id': message.id
        }

        await self.guilds.insert_one(guilds_entry)

        await success_embed(interaction, 'All done! You can now add roles with the \'/rr add\' command')

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def add(self, interaction: Interaction):
        """Adds a role to ReactionRoles."""

        if not await self.guilds.find_one({'guild_id': interaction.guild.id}):
            return await error_embed(interaction, 'Please setup reaction roles first using /rr setup')

        await green_embed(interaction, 'Type in the name of the role')

        def name_check(m):
            return len(m.content) < 256 and m.channel == interaction.channel and m.author == interaction.user

        name_message = await self.bot.wait_for('message', check=name_check, timeout=60)
        name = name_message.content

        channel = interaction.channel

        reaction_message = await green_embed(
            channel,
            'React to this message with an emote you want to associate with the role\n'
            '(the bot must be able to use that emote)'
        )

        while True:
            def emote_check(r, u):
                return r.message.id == reaction_message.id and u.id == interaction.user.id

            reaction, _ = await self.bot.wait_for('reaction_add', check=emote_check, timeout=120)

            if not reaction.emoji.available or reaction.emoji.managed:
                await channel.send('I can\'t use this emote, please choose a different one!', delete_after=3)
                continue

            break

        await green_embed(channel, 'Type in a color for the role(in hex) for example: #17A2E3')

        def color_check(message):
            return search(r'^#?[0-9a-fA-F]{6}$', message.content) is not None

        color = await self.bot.wait_for('message', check=color_check, timeout=120)
        color = int(color.content[-6:], 16)  # To hex

        embed = discord.Embed(
            description=f'**Name:** {name}\n**Reaction**: {reaction}\n\n**Add the role?**',
            color=color
        )
        view = YesNoView(interaction.user.id)
        confirmation_message = await channel.send(embed=embed, view=view)

        await view.wait()

        if view.value is None:
            await view.disable_buttons(confirmation_message)

            return await error_embed(channel, f'{interaction.user.mention} you took too long to answer!')

        if not view.value:
            return

        try:
            role = await interaction.guild.create_role(name=name, color=discord.Color(color), mentionable=True)
        except discord.Forbidden:
            return await error_embed(channel, 'I don\'t have permissions to create the role!')

        reactions_entry = {
            'guild_id': interaction.guild.id,
            'role_id': role.id,
            'emote': str(reaction)
        }

        await self.reactions.insert_one(reactions_entry)

        embed_message = await self.get_embed_message(interaction.guild)
        if embed_message is None:
            return await error_embed(interaction, 'Couldn\'t find the Reaction Roles embed message!')

        await self.add_role_to_embed(embed_message, name, reaction)

        await success_embed(channel, 'Role added!')

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(
        role='The role to remove from Reaction Roles',
    )
    async def remove(self, interaction: Interaction, role: discord.Role):
        """Removes a role from ReactionRoles."""

        if not await self.guilds.find_one({'guild_id': interaction.guild.id}):
            return await error_embed(interaction, 'Please setup reaction roles first using /rr setup')

        try:
            await role.delete()
        except discord.Forbidden:
            return await error_embed(interaction, 'I don\'t have permissions to delete the role!')

        await self.reactions.delete_one({'guild_id': interaction.guild.id, 'role_id': role.id})

        embed_message = await self.get_embed_message(interaction.guild)
        if embed_message is None:
            return await error_embed(interaction, 'Couldn\'t find the Reaction Roles embed message!')

        await self.remove_role_from_embed(embed_message, role.name)

        await success_embed(interaction, 'Role removed!')

    @command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def reset(self, interaction: Interaction):
        """Resets ReactionRoles."""

        guild_id = interaction.guild.id
        if not await self.guilds.find_one({'guild_id': guild_id}):
            return await error_embed(interaction, 'Please setup reaction roles first using /rr setup')

        view = YesNoView(interaction.user.id)
        await green_embed(interaction, '**Are you sure?**', view=view)

        await view.wait()

        if view.value is None:
            return await error_embed(interaction, f'{interaction.user.mention} you took too long to answer!')

        if not view.value:
            return

        # Clear embed
        embed_message = await self.get_embed_message(interaction.guild)
        if embed_message is not None:
            await embed_message.delete()

        # Remove roles
        roles = await self.reactions.find({'guild_id': guild_id})
        async for role in roles:
            role_to_remove = interaction.guild.get_role(role['role_id'])
            await role_to_remove.delete()

        # Clear database
        await self.reactions.delete_many({'guild_id': guild_id})
        await self.guilds.delete_one({'guild_id': guild_id})


async def setup(bot: 'NextBot'):
    await bot.add_cog(ReactionRoles(bot))
