from logging import getLogger

from discord import ButtonStyle, Interaction, Message, HTTPException, Forbidden
from discord.ui import View, Button, button, Modal, TextInput

from utils.embeds import error_embed

log = getLogger(__name__)

__all__ = ('YesNoView', 'QueryModal')


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
