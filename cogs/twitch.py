from datetime import datetime
from os import getenv
from random import random
from typing import TYPE_CHECKING
from urllib.parse import quote

import discord
from discord import app_commands, Interaction
from discord.app_commands import command
from discord.ext.commands import GroupCog
from discord.ext.tasks import loop
from motor.motor_asyncio import AsyncIOMotorCollection

from utils.embeds import *

if TYPE_CHECKING:
    from nextbot import NextBot

BASE_URL = 'https://api.twitch.tv/helix/'

HEADERS = {
    'Client-ID': getenv('TWITCH_CLIENT_ID'),
    'Authorization': f'Bearer {getenv("TWITCH_TOKEN")}'
}


class Twitch(GroupCog, name='twitch'):
    bot: 'NextBot'
    twitch_notifs: AsyncIOMotorCollection

    def __init__(self, bot: 'NextBot'):
        self.bot = bot
        self.twitch_notifs = self.bot.db['twitch_notifs']

    async def cog_load(self):
        """Starts the background task."""

        self.check_live.start()

    async def fetch(self, endpoint: str, params: dict[str, str]) -> dict | None:
        """Fetches data from the Twitch API."""

        async with self.bot.session.get(BASE_URL + endpoint, params=params, headers=HEADERS) as resp:
            response = await resp.json()
            if 'data' in response:
                return response['data'] if response['data'] else None

    async def fetch_twitch_user(self, user: str) -> dict | None:
        """Fetches the Twitch user from the Twitch API."""

        return await self.fetch('users', {'login': quote(user)})

    async def fetch_user_avatar(self, user: str) -> str | None:
        """Fetches the user's avatar url."""

        user_dict = await self.fetch_twitch_user(user)
        return user_dict[0]['profile_image_url'] if user_dict is not None else None

    async def fetch_live_status(self, user: str) -> dict | None:
        """Checks if the user is live and returns the stream info object."""

        return await self.fetch('streams', {'user_login': quote(user)})

    async def fetch_game(self, game_name: str) -> dict | None:
        """Fetches the Game object from the Twitch API."""

        return await self.fetch('games', {'name': quote(game_name)})

    async def fetch_streams(self, game_id: str) -> dict | None:
        """Fetches the Stream object from the Twitch API."""

        return await self.fetch('streams', {'game_id': game_id, 'first': '6'})

    async def send_notification(self, user: discord.User, message: str, where: str | dict, data: dict):
        """Sends the notification."""

        game_name = data['game_name']
        date = datetime.strptime(data['started_at'], '%Y-%m-%dT%H:%M:%SZ')
        date_text = date.strftime('%B %d, %Y at %H:%M')
        thumbnail_url = data['thumbnail_url']
        title = data['title']
        name = data['user_name']

        embed = discord.Embed(
            color=0x6d3ee3,
            title=f'{name} is now streaming!',
            description=f'https://www.twitch.tv/{name.lower()}\n\n**Stream title**: {title}'
        )
        embed.add_field(name='Playing', value=game_name)
        embed.add_field(name='Started at', value=date_text)

        cache_buster = f'?rnd={int(random() * 10000000000000000)}'
        embed.set_image(url=thumbnail_url.replace('{width}', '880').replace('{height}', '496') + cache_buster)
        embed.set_thumbnail(url=await self.fetch_user_avatar(name))

        if where == 'dm':
            if not user.dm_channel:
                await user.create_dm()

            await user.dm_channel.send(message, embed=embed)
        else:
            guild = self.bot.get_guild(where['guild_id'])
            channel = guild.get_channel(where['channel_id'])
            await channel.send(message, embed=embed)

    async def check_on_start(self):
        """Checks for live streamers on startup."""

        users = self.twitch_notifs.find({})

        async for user in users:
            live_status = await self.fetch_live_status(user['twitch_user'])
            if live_status is not None and not user['is_live']:
                await self.twitch_notifs.update_one(
                    {'user_id': user['user_id'], 'twitch_user': user['twitch_user']},
                    {'$set': {'is_live': True}}
                )

            elif live_status is None and user['is_live']:
                await self.twitch_notifs.update_one(
                    {'user_id': user['user_id'], 'twitch_user': user['twitch_user']},
                    {'$set': {'is_live': False}}
                )

    async def is_in_db(self, user_id: int, twitch_user: str) -> bool:
        return True if await self.twitch_notifs.find_one({'user_id': user_id, 'twitch_user': twitch_user}) else False

    @loop(seconds=60)
    async def check_live(self):
        """Checks for live streamers every 60 seconds."""

        users = self.twitch_notifs.find({})

        async for user in users:
            live_status = await self.fetch_live_status(user['twitch_user'])
            if live_status is not None and not user['is_live']:
                user_to_notify = self.bot.get_user(user['user_id'])
                message = user['message'].replace('<mention>', user_to_notify.mention)

                await self.send_notification(user_to_notify, message, user['where'], live_status[0])

                await self.twitch_notifs.update_one(
                    {'user_id': user['user_id'], 'twitch_user': user['twitch_user']},
                    {'$set': {'is_live': True}}
                )

                print(f'{user["twitch_user"]} went live!')
            elif live_status is None and user['is_live']:
                await self.twitch_notifs.update_one(
                    {'user_id': user['user_id'], 'twitch_user': user['twitch_user']},
                    {'$set': {'is_live': False}}
                )

                print(f'{user["twitch_user"]} stopped streaming.')

    @check_live.before_loop
    async def before_check_live(self):
        """Initiates the check on start."""

        await self.check_on_start()
        await self.bot.wait_until_ready()

    @command()
    @app_commands.describe(
        channel='The channel to send the notifications to. If left empty it will send them in DMs',
        twitch_user='The Twitch username of the streamer you want to receive notifications for',
        message='The message being sent each notification. "<mention>" will be replaced with a @mention of you'
    )
    async def notify(
            self,
            interaction: Interaction,
            channel: discord.TextChannel | None,
            twitch_user: str,
            message: str = '<mention>'
    ):
        """Sets up the notification."""

        if await self.fetch_twitch_user(twitch_user) is None:
            return await error_embed(interaction, 'Invalid Twitch user!')

        notifs_entry = {
            'user_id': interaction.user.id,
            'twitch_user': twitch_user.lower(),
            'message': message,
            'is_live': bool(await self.fetch_live_status(twitch_user)),
            'where': {
                'guild_id': interaction.guild.id,
                'channel_id': channel.id
            } if channel is not None else 'dm'
        }

        await self.twitch_notifs.insert_one(notifs_entry)
        await success_embed(interaction, f'Successfully set your notification for `{twitch_user}`!')

    @command()
    @app_commands.describe(
        twitch_user='The Twitch username of the streamer you want to edit the notification for',
        channel='The new channel you want to set. Leave empty to change the message only',
        message='The new message you want to set. Leave empty to change the channel only',
    )
    async def edit(
            self,
            interaction: Interaction,
            twitch_user: str,
            channel: discord.TextChannel = None,
            message: str = None
    ):
        """Edits a notification message."""

        if channel is None and message is None:
            return await error_embed(interaction, 'You can\'t leave both of the options empty!')

        twitch_user = twitch_user.lower()
        if not await self.is_in_db(interaction.user.id, twitch_user):
            return await error_embed(interaction, f'You don\'t have a notification setup for `{twitch_user}`!')

        set_query = {}
        if message is not None:
            set_query['message'] = message
        if channel is not None:
            set_query['where'] = {'guild_id': interaction.guild.id, 'channel_id': channel.id}

        await self.twitch_notifs.update_one(
            {'user_id': interaction.user.id, 'twitch_user': twitch_user},
            {'$set': set_query}
        )

        await success_embed(interaction, f'Successfully edited the notification!')

    @command()
    @app_commands.describe(twitch_user='The Twitch username of the streamer you want to remove the notification for')
    async def remove(self, interaction: Interaction, twitch_user: str):
        """Removes a notification."""

        twitch_user = twitch_user.lower()
        if not await self.is_in_db(interaction.user.id, twitch_user):
            return await error_embed(interaction, f'You don\'t have a notification setup for `{twitch_user}`!')

        await self.twitch_notifs.delete_one({'user_id': interaction.user.id, 'twitch_user': twitch_user})

        await success_embed(interaction, 'Successfully removed the notification!')

    @command()
    @app_commands.describe(game='The game to show the streams')
    async def streams(self, interaction: Interaction, game: str):
        """Shows the top 5 streams for a game."""

        game_info = await self.fetch_game(game)
        if not game_info:
            return await error_embed(interaction, 'Game not found!')

        game_info = game_info[0]
        game_name = game_info['name']
        game_image_url = game_info['box_art_url'].replace('{width}', '432').replace('{height}', '576')

        streams = await self.fetch_streams(game_info['id'])
        if not streams:
            return await error_embed(interaction, f'No streams found for **{game_name}**')

        embed = Embed()
        embed.set_author(
            name=f'{game_name} streams',
            url=f'https://www.twitch.tv/directory/game/{game}',
            icon_url=self.bot.user.avatar.url
        )
        embed.set_image(url=game_image_url)

        for stream in streams[:5]:
            user_name = stream['user_name']
            title = stream['title']
            viewer_count = stream['viewer_count']
            embed.add_field(
                name=f'**{user_name}**',
                value=f'{viewer_count} viewers -[**{title}**](https://twitch.tv/{user_name})',
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: 'NextBot'):
    await bot.add_cog(Twitch(bot))
