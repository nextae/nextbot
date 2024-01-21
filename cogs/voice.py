from asyncio import run_coroutine_threadsafe
from datetime import timedelta
from logging import getLogger
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from discord import app_commands, Interaction, Member, VoiceState, VoiceClient, VoiceChannel
from discord.app_commands import command
from discord.ext.commands import Cog, command as normal_command
from discord.utils import get

from utils.checks import is_next
from utils.embeds import *
from utils.voice_classes import AudioSource, YouTubeData, TTSData

if TYPE_CHECKING:
    from nextbot import NextBot

log = getLogger(__name__)


class Voice(Cog):
    bot: 'NextBot'
    tts_enabled: bool = True
    _queue: dict[int, list[YouTubeData | TTSData]] = dict()
    _loops: set[int] = set()

    def __init__(self, bot: 'NextBot'):
        self.bot = bot

    @staticmethod
    def parse_duration(duration: int) -> str:
        """Parses the duration to a readable string."""

        return str(timedelta(seconds=duration)).lstrip('0:')

    async def youtube_embed(self, data: YouTubeData) -> Embed:
        """Creates an Embed with the song information."""

        embed = Embed(title=data.title, url=data.url)

        embed.set_thumbnail(url=data.thumbnail_url)
        embed.add_field(name='Channel', value=data.channel)
        embed.add_field(name='Duration', value=self.parse_duration(data.duration))

        return embed

    @staticmethod
    async def tts_embed(data: TTSData) -> Embed:
        """Creates an Embed with the TTS message information."""

        return Embed(title='TTS Message:', description=data.text)

    @staticmethod
    def data_string(data: YouTubeData | TTSData) -> str:
        """Returns a short string representing the data."""

        if isinstance(data, YouTubeData):
            return f'**[{data.title}]({data.url})**'
        elif isinstance(data, TTSData):
            text = f'{data.text[:30] + "..." if len(data.text) > 30 else data.text[:30]}'
            return f'**TTS Message:** {text}'
        else:
            return ''

    async def handle_queue(self, error: Exception, voice_client: VoiceClient):
        """Handles the queue, called when an audio source finishes."""

        if error is not None:
            log.error(error)
            return

        guild_id = voice_client.guild.id
        if guild_id not in self._queue:
            return

        if self._queue[guild_id]:
            finished_source = self._queue[guild_id].pop(0)
            if guild_id in self._loops:
                self._queue[guild_id].append(finished_source)

            if not self._queue[guild_id]:
                del self._queue[guild_id]
                return

            await self.play_audio_source(voice_client, self._queue[guild_id][0])
        else:
            del self._queue[guild_id]

    async def play_audio_source(self, voice_client: VoiceClient, data: YouTubeData | TTSData):
        """Plays a source in the specified VoiceClient."""

        def after(error: Exception):
            fut = run_coroutine_threadsafe(self.handle_queue(error, voice_client), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                log.error(e)

        voice_client.play(AudioSource(data), after=after)

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        """Disconnects from voice if all other users left."""

        if before.channel is not None and len(before.channel.members) == 1 and self.bot.user in before.channel.members:
            voice_client = get(self.bot.voice_clients, channel=before.channel)
            await voice_client.disconnect(force=False)

            guild_id = member.guild.id
            if guild_id in self._queue:
                del self._queue[guild_id]

        # Deletes the queue if the bot got disconnected
        if member == member.guild.me and after.channel is None:
            guild_id = member.guild.id
            if guild_id in self._queue:
                del self._queue[guild_id]

    @command()
    @app_commands.guild_only()
    @app_commands.describe(query='The TTS message to play')
    async def tts(self, interaction: Interaction, query: str):
        """Sends a TTS message."""

        user = interaction.user
        if user.voice is None:
            return await error_embed(interaction, 'You need to be in a voice channel!')

        guild_id = interaction.guild.id

        if guild_id in self._queue:
            voice_client: VoiceClient = interaction.guild.voice_client

            if user not in voice_client.channel.members:
                return await error_embed(interaction, 'You need to be in the voice channel to use this command!')

            data = TTSData(query)
            self._queue[guild_id].append(data)

            embed = await self.tts_embed(data)
            embed.set_author(name='Added to queue:', icon_url=self.bot.user.avatar.url)
            await interaction.response.send_message(embed=embed)
        else:
            voice_client = interaction.guild.voice_client or await user.voice.channel.connect()
            data = TTSData(query)
            self._queue[guild_id] = [data]

            try:
                await self.play_audio_source(voice_client, data)
            except Exception as e:
                return await error_embed(interaction, str(e))

            embed = await self.tts_embed(data)
            embed.set_author(name='Now playing:', icon_url=self.bot.user.avatar.url)
            await interaction.response.send_message(embed=embed)

    @command()
    @app_commands.guild_only()
    @app_commands.describe(channel='The channel to play the TTS message', query='The TTS message to play')
    async def tts_channel(self, interaction: Interaction, channel: VoiceChannel, query: str):
        """Sends a TTS message in the target channel."""

        if not channel.members:
            return await error_embed(interaction, 'Channel is empty!')

        guild_id = interaction.guild.id

        if guild_id in self._queue:
            voice_client = interaction.guild.voice_client

            if channel != voice_client.channel:
                return await error_embed(interaction, 'The bot is currently being used in a different channel!')

            data = TTSData(query)
            self._queue[guild_id].append(data)

            embed = await self.tts_embed(data)
            embed.set_author(name='Added to queue:', icon_url=self.bot.user.avatar.url)
            await interaction.response.send_message(embed=embed)
        else:
            voice_client = interaction.guild.voice_client or await channel.connect()
            data = TTSData(query)
            self._queue[guild_id] = [data]

            try:
                await self.play_audio_source(voice_client, data)
            except Exception as e:
                return await error_embed(interaction, str(e))

            embed = await self.tts_embed(data)
            embed.set_author(name='Now playing:', icon_url=self.bot.user.avatar.url)
            await interaction.response.send_message(embed=embed)

    @command()
    @app_commands.guild_only()
    async def join(self, interaction: Interaction):
        """Joins the voice channel."""

        if interaction.guild.voice_client is not None:
            return await error_embed(interaction, 'The bot is already in a voice channel!')

        user = interaction.user
        if user.voice is not None:
            await user.voice.channel.connect()
        else:
            return await error_embed(interaction, 'You are not in a voice channel!')

    @command()
    @app_commands.guild_only()
    async def stop(self, interaction: Interaction):
        """Stops the audio."""

        voice_client: VoiceClient = interaction.guild.voice_client
        if voice_client is None:
            return await error_embed(interaction, 'The bot is not connected to a voice channel!')

        voice_client.stop()

        guild_id = interaction.guild.id
        if guild_id in self._queue:
            del self._queue[guild_id]

        await green_embed(interaction, f'⏹️ Stopped!')

    @command()
    @app_commands.guild_only()
    async def leave(self, interaction: Interaction):
        """Disconnects the bot from voice chat."""

        voice_client = interaction.guild.voice_client
        if voice_client is None:
            return await error_embed(interaction, 'The bot is not connected to a voice channel!')

        await voice_client.disconnect(force=False)

        guild_id = interaction.guild.id
        if guild_id in self._queue:
            del self._queue[guild_id]

        await green_embed(interaction, 'Disconnected!')

    @command()
    @app_commands.guild_only()
    @app_commands.describe(query='The YouTube link or query to search')
    async def play(self, interaction: Interaction, query: str):
        """Plays a query from YouTube."""

        user = interaction.user
        if user.voice is None:
            return await error_embed(interaction, 'You need to be in a voice channel!')

        hostname = urlparse(query).hostname
        if hostname is not None and hostname.lstrip('www.') not in ('youtube.com', 'youtu.be', 'music.youtube.com'):
            return await error_embed(interaction, 'Invalid YouTube link!')

        await interaction.response.defer()

        guild_id = interaction.guild.id

        if guild_id in self._queue:
            voice_client: VoiceClient = interaction.guild.voice_client

            if user not in voice_client.channel.members:
                return await error_embed(interaction, 'You need to be in the voice channel to add songs to the queue!')
            try:
                data = await YouTubeData.from_query(query, loop=self.bot.loop)
            except Exception as e:
                return await error_embed(interaction, str(e))

            embed = await self.youtube_embed(data)
            embed.set_author(name='Added to queue:', icon_url=self.bot.user.avatar.url)
            await interaction.followup.send(embed=embed)

            self._queue[guild_id].append(data)
        else:
            try:
                data = await YouTubeData.from_query(query, loop=self.bot.loop)
            except Exception as e:
                return await error_embed(interaction, str(e))

            embed = await self.youtube_embed(data)
            embed.set_author(name='Now playing:', icon_url=self.bot.user.avatar.url)
            await interaction.followup.send(embed=embed)

            voice_client = interaction.guild.voice_client or await user.voice.channel.connect()
            self._queue[guild_id] = [data]

            try:
                await self.play_audio_source(voice_client, data)
            except Exception as e:
                return await error_embed(interaction, str(e))

    @command()
    @app_commands.guild_only()
    async def pause(self, interaction: Interaction):
        """Pauses the song."""

        voice_client: VoiceClient = interaction.guild.voice_client
        if voice_client is None:
            return await error_embed(interaction, 'The bot is not connected to a voice channel!')

        if interaction.user not in voice_client.channel.members:
            return await error_embed(interaction, 'You need to be in the voice channel to use this command!')

        if voice_client.is_playing():
            voice_client.pause()
            await green_embed(interaction, '⏸ Paused!')
        else:
            await error_embed(interaction, 'Already paused!')

    @command()
    @app_commands.guild_only()
    async def resume(self, interaction: Interaction):
        """Resumes the song."""

        voice_client: VoiceClient = interaction.guild.voice_client
        if voice_client is None:
            return await error_embed(interaction, 'The bot is not connected to a voice channel!')

        if interaction.user not in voice_client.channel.members:
            return await error_embed(interaction, 'You need to be in the voice channel to use this command!')

        if voice_client.is_paused():
            voice_client.resume()
            await green_embed(interaction, '▶ Resumed!')
        else:
            await error_embed(interaction, 'Already playing!')

    @command()
    @app_commands.guild_only()
    async def skip(self, interaction: Interaction):
        """Skips the song."""

        voice_client: VoiceClient = interaction.guild.voice_client
        if voice_client is None:
            return await error_embed(interaction, 'The bot is not connected to a voice channel!')

        if interaction.user not in voice_client.channel.members:
            return await error_embed(interaction, 'You need to be in the voice channel to use this command!')

        voice_client.stop()

        await green_embed(interaction, f'⏩ Skipped!')

    @command()
    @app_commands.guild_only()
    async def queue(self, interaction: Interaction):
        """Shows the queue for the guild."""

        guild_id = interaction.guild.id
        if guild_id not in self._queue:
            return await error_embed(interaction, 'There is no queue!')

        queue = self._queue[guild_id]
        if not queue:
            del self._queue[guild_id]
            return await error_embed(interaction, 'There is no queue!')

        currently_playing = queue[0]
        description = f'Currently playing: {self.data_string(currently_playing)}\n\n'
        for i, data in enumerate(queue[1:]):
            if isinstance(data, YouTubeData):
                description += f'`{i + 1}.` {self.data_string(data)} | {self.parse_duration(data.duration)}\n'
            else:
                description += f'`{i + 1}.` {self.data_string(data)}\n'

        await interaction.response.send_message(embed=Embed(title='Queue', description=description))

    @command()
    @app_commands.guild_only()
    @app_commands.describe(number='The number of entry to remove from the queue')
    async def remove(self, interaction: Interaction, number: int):
        """Removes an entry from the queue."""

        guild_id = interaction.guild.id
        if guild_id not in self._queue:
            return await error_embed(interaction, 'There is no queue!')

        if number not in range(1, len(self._queue[guild_id])):
            return await error_embed(interaction, 'Invalid number to remove!')

        data = self._queue[guild_id].pop(number)
        await green_embed(interaction, f'Successfully removed {self.data_string(data)} from the queue!')

    @command()
    @app_commands.guild_only()
    @app_commands.describe(volume='The volume to change to. Leave empty to check the current volume')
    async def volume(self, interaction: Interaction, volume: int = None):
        """Changes the sound volume."""

        voice_client: VoiceClient = interaction.guild.voice_client
        if voice_client is None:
            return await error_embed(interaction, 'The bot is not connected to a voice channel!')

        if interaction.user not in voice_client.channel.members:
            return await error_embed(interaction, 'You need to be in the voice channel to use this command!')

        if volume is None:
            return await green_embed(
                interaction,
                f'🔊 Volume is currently set to {int(voice_client.source.volume * 100)}%'
            )

        if volume not in range(0, 101) and interaction.user.id != 342782256001187840:
            return await error_embed(interaction, 'Volume needs to be in range 0-100')

        voice_client.source.volume = volume / 100
        await green_embed(interaction, f'🔊 Set volume to {volume}%')

    @command()
    @app_commands.guild_only()
    async def loop(self, interaction: Interaction):
        """Enables/disables queue loop."""

        voice_client: VoiceClient = interaction.guild.voice_client
        if voice_client is None:
            return await error_embed(interaction, 'The bot is not connected to a voice channel!')

        if interaction.user not in voice_client.channel.members:
            return await error_embed(interaction, 'You need to be in the voice channel to use this command!')

        guild_id = interaction.guild.id
        if guild_id in self._loops:
            self._loops.remove(guild_id)
            await green_embed(interaction, f'🔁 Loop disabled!')
        else:
            self._loops.add(guild_id)
            await green_embed(interaction, f'🔁 Loop enabled!')

    @normal_command(name='enabletts')
    @is_next()
    async def enable_tts(self, ctx):
        """Enables TTS."""

        self.tts_enabled = True
        print('TTS enabled')

    @normal_command(name='disabletts')
    @is_next()
    async def disable_tts(self, ctx):
        """Disables TTS."""

        self.tts_enabled = False
        print('TTS disabled')


async def setup(bot: 'NextBot'):
    await bot.add_cog(Voice(bot))
