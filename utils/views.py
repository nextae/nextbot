import math
from logging import getLogger
from typing import TYPE_CHECKING, Any, Generator, Callable

import discord
from discord import ButtonStyle, Interaction, Message, HTTPException, Forbidden
from discord.ui import View, Button, button, Modal, TextInput, Select, select

from utils.embeds import error_embed, green_embed, Embed

if TYPE_CHECKING:
    from nextbot import NextBot

log = getLogger(__name__)

__all__ = (
    'YesNoView',
    'QueryModal',
    'RolesView',
    'PaginationView'
)


class YesNoView(View):
    def __init__(self, user_id: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.value = None
        self.user_id = user_id

    @button(label='Yes', style=ButtonStyle.green, custom_id='confirm_yes')
    async def yes(self, interaction: Interaction, btn: Button):
        if interaction.user.id != self.user_id:
            return await error_embed(interaction, 'You are not allowed to confirm this!')

        btn.disabled = True
        self.no.disabled = True
        await interaction.response.edit_message(view=self)
        self.value = True
        self.stop()

    @button(label='No', style=ButtonStyle.grey, custom_id='confirm_no')
    async def no(self, interaction: Interaction, btn: Button):
        if interaction.user.id != self.user_id:
            return await error_embed(interaction, 'You are not allowed to decline this!')

        btn.disabled = True
        self.yes.disabled = True
        await interaction.response.edit_message(view=self)
        self.value = False
        self.stop()

    async def disable_buttons(self, message: Message):
        """Disables the buttons."""

        self.yes.disabled = True
        self.no.disabled = True

        try:
            await message.edit(view=self)
        except (Forbidden, HTTPException):
            pass


class QueryModal(Modal, title='Emote'):
    query = TextInput(label='Query', placeholder='Type the FFZ emote query here...', max_length=50)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()

    async def on_error(self, interaction: Interaction, error: Exception):
        log.error(error)


class RolesView(View):
    def __init__(self, bot: 'NextBot', roles: list[dict] = None, first_setup: bool = False):
        self.bot = bot
        super().__init__(timeout=None)

        if first_setup:
            self.roles_add.add_option(label='Empty', description='Add roles with the /roles add command!')
            self.roles_remove.add_option(label='Empty', description='Add roles with the /roles add command!')

        if roles is None:
            return

        for role_entry in roles:
            emote = role_entry.get('emote')

            label = role_entry.get('name')
            value = str(role_entry.get('role_id'))
            description = role_entry.get('description')
            emote = self.bot.get_emoji(emote) if isinstance(emote, int) else emote

            self.roles_add.add_option(label=label, value=value, description=description, emoji=emote)
            self.roles_remove.add_option(label=label, value=value, description=description, emoji=emote)

        self.roles_add.max_values = len(roles)
        self.roles_remove.max_values = len(roles)

    @select(placeholder='Select the roles to add', custom_id='roles_add_select')
    async def roles_add(self, interaction: Interaction, s: Select):
        member = interaction.user
        guild = interaction.guild

        role_ids_to_add = {int(role_id) for role_id in s.values}

        roles_to_add = []
        roles_not_found = []
        for role_id in role_ids_to_add:
            role = guild.get_role(role_id)

            if role is not None:
                if role not in member.roles:
                    roles_to_add.append(role)
            else:
                roles_not_found.append(discord.utils.get(s.options, value=str(role_id)).label)

        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, atomic=False)
            except (Forbidden, HTTPException):
                return await error_embed(
                    interaction, 'I couldn\'t add the roles! Probably missing permissions', ephemeral=True
                )

        description = ''
        if roles_to_add:
            roles_text = '\n'.join(role.mention for role in roles_to_add)
            description += f'Successfully added the following roles:\n{roles_text}\n\n'

        if roles_not_found:
            roles_text = '\n'.join(roles_not_found)
            description += f'The following roles have not been found in the server:\n{roles_text}'

        if not description:
            return await green_embed(interaction, 'You already have all of the selected roles', ephemeral=True)

        await green_embed(interaction, description, ephemeral=True)

    @select(placeholder='Select the roles to remove', custom_id='roles_remove_select')
    async def roles_remove(self, interaction: Interaction, s: Select):
        member = interaction.user
        guild = interaction.guild

        role_ids_to_remove = {int(role_id) for role_id in s.values}

        roles_to_remove = []
        roles_not_found = []
        for role_id in role_ids_to_remove:
            role = guild.get_role(role_id)

            if role is not None:
                if role in member.roles:
                    roles_to_remove.append(role)
            else:
                roles_not_found.append(discord.utils.get(s.options, value=str(role_id)).label)

        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, atomic=False)
            except (Forbidden, HTTPException):
                return await error_embed(
                    interaction, 'I couldn\'t remove the roles! Probably missing permissions', ephemeral=True
                )

        description = ''
        if roles_to_remove:
            roles_text = '\n'.join(role.mention for role in roles_to_remove)
            description += f'Successfully removed the following roles:\n{roles_text}\n\n'

        if roles_not_found:
            roles_text = '\n'.join(roles_not_found)
            description += f'The following roles have not been found in the server:\n{roles_text}'

        if not description:
            return await green_embed(interaction, 'You already don\'t have any of the selected roles', ephemeral=True)

        await green_embed(interaction, description, ephemeral=True)


class PaginationView(View):
    def __init__(
        self,
        title: str,
        data: list[Any],
        per_page: int,
        entry_generator: Callable[[Any], Generator[str, None, None]],
        interaction: Interaction = None,
        description: str = None,
        thumbnail_url: str = None
    ):
        super().__init__(timeout=600)

        self.title = title
        self.description = description
        self.data = data
        self.per_page = per_page
        self.pages = math.ceil(len(data) / per_page) or 1
        self.generator = entry_generator
        self.interaction = interaction
        self.thumbnail_url = thumbnail_url

        self.current_page = 0
        self.update_buttons()

    async def on_timeout(self) -> None:
        """Disables the buttons."""

        if self.interaction is None:
            return

        try:
            message = await self.interaction.original_response()
        except discord.HTTPException:
            return

        self.previous.disabled = True
        self.next.disabled = True
        try:
            await message.edit(view=self)
        except discord.HTTPException:
            pass

    def update_buttons(self):
        """Updates the View data based on the current page."""

        self.current_info.label = f'Page {self.current_page + 1}/{self.pages}'
        self.previous.disabled = self.current_page == 0
        self.next.disabled = self.current_page == self.pages - 1

    def embed(self) -> discord.Embed:
        """Creates an embed for the current page."""

        data = self.data[self.current_page * self.per_page : (self.current_page + 1) * self.per_page]
        embed = Embed(
            title=self.title,
            description=(self.description or '') + '\n'.join(
                f'{i + self.current_page * self.per_page}. {entry}'
                for i, entry in enumerate(self.generator(data), 1)
            )
        )
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)

        return embed

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji='⬅', custom_id='previous_page')
    async def previous(self, interaction: Interaction, btn: discord.ui.Button):
        """Goes to the previous page."""

        if self.interaction is not None and interaction.user.id != self.interaction.user.id:
            return await error_embed(interaction, 'You are not allowed to do this!')

        self.current_page -= 1
        self.update_buttons()

        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, disabled=True)
    async def current_info(self, interaction: Interaction, btn: discord.ui.Button):
        """Displays the current page."""

        pass

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji='➡', custom_id='next_page')
    async def next(self, interaction: Interaction, btn: discord.ui.Button):
        """Goes to the next page."""

        if self.interaction is not None and interaction.user.id != self.interaction.user.id:
            return await error_embed(interaction, 'You are not allowed to do this!')

        self.current_page += 1
        self.update_buttons()

        await interaction.response.edit_message(embed=self.embed(), view=self)
