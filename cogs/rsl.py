from typing import TYPE_CHECKING

from discord import Message, Member, Status, Guild, Emoji, VoiceState
from discord.ext.commands import Cog

from utils.embeds import *

if TYPE_CHECKING:
    from nextbot import NextBot
    
MOCTOLA_ID = 202850516554874880
THUNDER_ID = 220262967722115072
BOTS_CHANNEL_ID = 563872164235837500


class RSL(Cog):
    bot: 'NextBot'

    def __init__(self, bot: 'NextBot'):
        self.bot = bot
        
    def emote(self, emote_name: str) -> Emoji | str:
        """A shorter way to get an emote."""
        
        return self.bot.get_emote(emote_name)

    @Cog.listener('on_message_delete')
    async def moctola_exposer_message_delete(self, message: Message):
        """Detects when Moctola deletes a message."""
        
        if message.author.id != MOCTOLA_ID:
            return

        embed = Embed(title='Moctola exposer v1.2', description=f'Moctola just deleted: "{message.content}"')
        if message.attachments:
            image = await message.attachments[0].to_file()
            await message.channel.send(embed=embed, file=image)
        else:
            await message.channel.send(embed=embed)

    @Cog.listener('on_message_edit')
    async def moctola_exposer_message_edit(self, before: Message, after: Message):
        """Detects when Moctola edits a message."""
        
        if after.author.id != MOCTOLA_ID or before.content == after.content:
            return

        embed = Embed(title='Moctola exposer v1.2', description=f'Moctola just edited: "{before.content}"')
        await after.channel.send(embed=embed)
    
    @staticmethod
    async def send_scooby_stalker_message(guild: Guild, message_text: str):
        """Sends a Scooby-Stalker message to the #bots channel."""

        bots_channel = guild.get_channel(BOTS_CHANNEL_ID)
        if bots_channel is None:
            return

        embed = Embed(title='Scooby-Stalker v1.0', description=message_text)
        await bots_channel.send(embed=embed)
        
    @Cog.listener('on_presence_update')
    async def scooby_stalker_presence_update(self, before: Member, after: Member):
        """Detects when Thunder changes his status."""

        if after.id != THUNDER_ID or after.status == before.status:
            return

        scooby_stalker_messages = {
            Status.online: f'Scooby-Jewington has gone online! {self.emote("PagMan")}',
            Status.offline: f'Scooby-Jewington has gone offline {self.emote("Sadge")}',
            Status.idle: f'Scooby-Jewington is now away.. probably went to the gym again {self.emote("pepeAgony")}',
            Status.dnd: f'Rare Scooby-Jewington do not disturb status {self.emote("PogU")}'
        }

        await self.send_scooby_stalker_message(after.guild, scooby_stalker_messages[after.status])
        
    @Cog.listener('on_voice_state_update')
    async def scooby_stalker_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        """Detects when Thunder changes his voice state."""

        if member.id != THUNDER_ID:
            return

        if before.channel is None and after.channel is not None:
            await self.send_scooby_stalker_message(
                member.guild,
                f'**GOLDEN LEGENDARY ULTRA RARE MOMENT!** '
                f'Scooby-Jewington has joined a voice channel {self.emote("xqcCheer")}'
            )

        if before.channel is not None and after.channel is None:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has left the voice channel {self.emote("Sadeg")}'
            )

        if not before.self_mute and after.self_mute:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has muted himself {self.emote("FeelsBadMan")}'
            )

        if before.self_mute and not after.self_mute:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has unmuted himself {self.emote("FeelsOkayMan")}'
            )

        if not before.self_deaf and after.self_deaf:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has deafened himself {self.emote("WeirdChamp")}'
            )

        if before.self_deaf and not after.self_deaf:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has undeafened himself {self.emote("HYPERS")}'
            )

        if not before.self_stream and after.self_stream:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has started streaming {self.emote("Pog")} '
                f'(surely it\'s Avatar {self.emote("COPIUM")})'
            )

        if before.self_stream and not after.self_stream:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has stopped streaming {self.emote("ResidentSleeper")}'
            )

        if not before.self_video and after.self_video:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has started sharing his cam {self.emote("GachiGasm")} '
                f'(wonder if he\'s naked or painting the wall mayhaps {self.emote("PauseChamp")})'
            )

        if before.self_video and not after.self_video:
            await self.send_scooby_stalker_message(
                member.guild,
                f'Scooby-Jewington has stopped sharing his cam {self.emote("gachiSad")}'
            )


async def setup(bot: 'NextBot'):
    await bot.add_cog(RSL(bot))
