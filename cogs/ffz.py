from io import BytesIO
from random import randrange
from typing import TYPE_CHECKING

from discord import app_commands, Interaction, File, Message, Forbidden, HTTPException
from discord.app_commands import command
from discord.ext.commands import Cog

from utils.embeds import error_embed, success_embed
from utils.views import YesNoView, QueryModal

if TYPE_CHECKING:
    from nextbot import NextBot

BASE_URL = 'https://api.frankerfacez.com/v1/'


class FFZ(Cog):
    bot: 'NextBot'

    def __init__(self, bot: 'NextBot'):
        self.bot = bot

        react_context_menu = app_commands.ContextMenu(name='React with FFZ emote', callback=self.react)
        self.bot.tree.add_command(react_context_menu)

    async def fetch_ffz(self, endpoint: str, params: dict[str, str]) -> dict:
        """Fetches an endpoint from the FFZ API."""

        async with self.bot.session.get(BASE_URL + endpoint, params=params) as response:
            return await response.json()

    async def fetch_image(self, url: str, data_type: str) -> bytes | BytesIO:
        """Fetches a url."""

        async with self.bot.session.get(url) as response:
            if data_type == 'file':
                return BytesIO(await response.read())

            if data_type == 'img':
                return await response.read()

    async def get_image(self, query: str, option: str | int, file_type: str) -> dict | None:
        """Gets an image from FFZ API."""

        params = {'q': query}

        if isinstance(option, int):
            params['sort'] = 'count-desc'

        data = await self.fetch_ffz('emoticons', params)
        if not data['emoticons']:
            return None

        if option == 'random':
            pages = data['_pages']
            if pages > 1:
                page = randrange(1, pages)
                params['page'] = str(page)
                data = await self.fetch_ffz('emoticons', params)  # fetches the randomized page

            index = randrange(0, len(data['emoticons']))
        else:
            index = option - 1
            if index >= len(data['emoticons']):
                return None

        # Gets the image_url from json data
        try:
            img_url = 'https:' + data['emoticons'][index]['urls']['2']
        except KeyError:
            img_url = 'https:' + data['emoticons'][index]['urls']['1']

        # Fetches image data
        image = await self.fetch_image(img_url, file_type)
        file_name = data['emoticons'][index]['name']

        return {'file': image, 'name': file_name}

    @command()
    @app_commands.describe(
        query='The emote to be displayed',
        number='Number of the emote to get, default 1',
        random='Select this if you want a random emote'
    )
    async def ffz(self, interaction: Interaction, query: str, number: int = None, random: bool = False):
        """Shows an emote from FFZ. Cannot have both number and random at the same time!"""

        if number is not None and random:
            return await error_embed(interaction, 'You can\'t select both a number and the `random` option!')

        if number is not None and number < 1:
            return await error_embed(interaction, 'Invalid option!')

        option = number or 'random' if random else 1

        data = await self.get_image(query, option, 'file')
        if data is None:
            return await error_embed(interaction, 'No results!')

        image = data['file']
        name = data['name']
        await interaction.response.send_message(file=File(image, f'{name}.png'))

    @command()
    @app_commands.describe(
        query='The emote to be uploaded',
        number='Number of the emote to get, default 1',
        random='Select this if you want a random emote'
    )
    async def upload(self, interaction: Interaction, query: str, number: int = None, random: bool = False):
        """Uploads an emote from FFZ. Cannot have both number and random at the same time!"""

        if number is not None and random:
            return await error_embed(interaction, 'You can\'t select both a number and the `random` option!')

        if number is not None and number < 1:
            return await error_embed(interaction, 'Invalid option!')

        option = number or 'random' if random else 1

        data = await self.get_image(query, option, 'file')
        if data is None:
            return await error_embed(interaction, 'No results!')

        image = data['file']
        name = data['name']
        await interaction.response.send_message(file=File(image, f'{name}.png'))

        emote_message = await interaction.original_response()

        view = YesNoView(interaction.user.id)
        confirmation_message = await interaction.channel.send('**Upload the emote?**', view=view)

        await view.wait()

        if view.value is None:
            try:
                await confirmation_message.delete()
            except HTTPException:
                pass

            return await error_embed(interaction, f'{interaction.user.mention} you took too long to answer!')

        if not view.value:
            return

        if not len([e for e in interaction.guild.emojis if not e.animated]) < interaction.guild.emoji_limit:
            return await error_embed(interaction, 'There is no space to upload the emote!')

        image = await emote_message.attachments[0].read()
        emote = await interaction.guild.create_custom_emoji(name=name, image=image)

        await success_embed(interaction, f'Successfully uploaded the emote: {emote}')

    async def react(self, interaction: Interaction, message: Message):
        """Reacts to the message with an emote from FFZ."""

        modal = QueryModal(timeout=30)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()

        if timed_out:
            return await error_embed(
                interaction,
                'You cancelled the modal or took too long to fill it, you have to try again!',
                ephemeral=True
            )

        data = await self.get_image(modal.query.value, 1, 'img')
        if data is None:
            return await error_embed(interaction, 'No results!', ephemeral=True)

        image = data['file']
        name = data['name']
        try:
            emote = await interaction.guild.create_custom_emoji(name=name, image=image)
        except Forbidden:
            return await error_embed(interaction, 'I don\'t have permissions to create an emote!', ephemeral=True)
        except HTTPException:
            return await error_embed(interaction, 'Adding an emote failed!', ephemeral=True)

        try:
            await message.add_reaction(emote)
        except Forbidden:
            return await error_embed(
                interaction,
                'I don\'t have permissions to add the emote to the message!',
                ephemeral=True
            )

        await emote.delete()


async def setup(bot: 'NextBot'):
    await bot.add_cog(FFZ(bot))
