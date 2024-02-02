from collections import defaultdict
from datetime import time
from logging import getLogger
from typing import TYPE_CHECKING, TypedDict, Literal

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.ext.commands import GroupCog, Context
from discord.ext.tasks import loop
from motor.core import AgnosticCollection

from utils.checks import is_next
from utils.embeds import green_embed, Embed
from utils.errors import interactions_error_handler
from utils.views import PaginationView

if TYPE_CHECKING:
    from nextbot import NextBot


log = getLogger(__name__)


class ChannelEntry(TypedDict):
    guild_id: int
    channel_id: int
    user_id: int
    messages: int
    words: int
    reactions: int
    files: int


Stat = Literal['Messages', 'Words', 'Reactions', 'Files']


class Stats(GroupCog, name='stats'):
    bot: 'NextBot'
    stats: AgnosticCollection
    stats_weekly: AgnosticCollection
    weekly_channels: AgnosticCollection

    def __init__(self, bot: 'NextBot'):
        self.bot = bot
        self.stats = self.bot.db['stats']
        self.stats_weekly = self.bot.db['stats_weekly']
        self.weekly_channels = self.bot.db['stats_weekly_channels']

        self.weekly_stats.start()

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Handles the errors."""

        if interaction.command.on_error is not None:
            return

        await interactions_error_handler(interaction, error)

    async def update_stats(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        messages: int = 0,
        words: int = 0,
        reactions: int = 0,
        files: int = 0
    ):
        """Updates the stats for the given channel id and user id. The values are the amount to increment by."""

        existing_entry = await self.stats.find_one({'channel_id': channel_id, 'user_id': user_id})
        if existing_entry is None:
            entry = ChannelEntry(
                guild_id=guild_id,
                channel_id=channel_id,
                user_id=user_id,
                messages=messages,
                words=words,
                reactions=reactions,
                files=files
            )

            return await self.stats.insert_one(entry)

        await self.stats.update_one(
            {'channel_id': channel_id, 'user_id': user_id},
            {'$inc': {'messages': messages, 'words': words, 'reactions': reactions, 'files': files}}
        )

    async def update_stats_weekly(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        messages: int = 0,
        words: int = 0,
        reactions: int = 0,
        files: int = 0
    ):
        """Updates the stats for the given channel id and user id. The values are the amount to increment by."""

        existing_entry = await self.stats_weekly.find_one({'channel_id': channel_id, 'user_id': user_id})
        if existing_entry is None:
            entry = ChannelEntry(
                guild_id=guild_id,
                channel_id=channel_id,
                user_id=user_id,
                messages=messages,
                words=words,
                reactions=reactions,
                files=files
            )

            return await self.stats_weekly.insert_one(entry)

        await self.stats_weekly.update_one(
            {'channel_id': channel_id, 'user_id': user_id},
            {'$inc': {'messages': messages, 'words': words, 'reactions': reactions, 'files': files}}
        )

    @GroupCog.listener('on_message')
    async def save_message(self, message: discord.Message):
        """Saves the message stats."""

        words = len(message.content.split()) if message.content else 0
        files = len(message.attachments)

        await self.update_stats(
            message.guild.id,
            message.channel.id,
            message.author.id,
            messages=1,
            words=words,
            files=files
        )
        await self.update_stats_weekly(
            message.guild.id,
            message.channel.id,
            message.author.id,
            messages=1,
            words=words,
            files=files
        )

    @GroupCog.listener('on_raw_message_delete')
    async def save_message_remove(self, payload: discord.RawMessageDeleteEvent):
        """Saves the removed message stats."""

        message = payload.cached_message
        if message is None:
            return

        words = -len(message.content.split()) if message.content else 0
        files = -len(message.attachments)

        await self.update_stats(
            payload.guild_id,
            payload.channel_id,
            message.author.id,
            messages=-1,
            words=words,
            files=files
        )
        await self.update_stats_weekly(
            payload.guild_id,
            payload.channel_id,
            message.author.id,
            messages=-1,
            words=words,
            files=files
        )

    @GroupCog.listener('on_message_edit')
    async def save_message_edit(self, before: discord.Message, after: discord.Message):
        """Saves the message edit stats."""

        before_words = len(before.content.split()) if before.content else 0
        after_words = len(after.content.split()) if after.content else 0

        if before_words != after_words:
            await self.update_stats(
                after.guild.id,
                after.channel.id,
                after.author.id,
                words=after_words - before_words
            )
            await self.update_stats_weekly(
                after.guild.id,
                after.channel.id,
                after.author.id,
                words=after_words - before_words
            )

    @GroupCog.listener('on_raw_reaction_add')
    async def save_reaction(self, payload: discord.RawReactionActionEvent):
        """Saves the reaction."""

        await self.update_stats(payload.guild_id, payload.channel_id, payload.user_id, reactions=1)
        await self.update_stats_weekly(payload.guild_id, payload.channel_id, payload.user_id, reactions=1)

    @GroupCog.listener('on_raw_reaction_remove')
    async def save_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Saves the reaction removal."""

        await self.update_stats(payload.guild_id, payload.channel_id, payload.user_id, reactions=-1)
        await self.update_stats_weekly(payload.guild_id, payload.channel_id, payload.user_id, reactions=-1)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(user='The user to check stats for', stat='The stat to check')
    async def user(self, interaction: Interaction, user: discord.Member = None, stat: Stat = None):
        """Check a user's stats."""

        user = user or interaction.user
        if stat is None:
            query = self.stats.aggregate([
                {'$match': {'guild_id': interaction.guild_id, 'user_id': user.id}},
                {
                    '$group': {
                        '_id': '$user_id',
                        'messages': {'$sum': '$messages'},
                        'words': {'$sum': '$words'},
                        'reactions': {'$sum': '$reactions'},
                        'files': {'$sum': '$files'}
                    }
                }
            ])

            async for entry in query:
                embed = Embed(
                    title='Overall Stats',
                    description=user.mention
                )
                embed.set_thumbnail(url=user.display_avatar.url)
                embed.add_field(name='Messages', value=f'{entry["messages"]:,}', inline=False)
                embed.add_field(name='Words', value=f'{entry["words"]:,}', inline=False)
                embed.add_field(name='Reactions', value=f'{entry["reactions"]:,}', inline=False)
                embed.add_field(name='Files', value=f'{entry["files"]:,}', inline=False)

                return await interaction.response.send_message(embed=embed)

        stat = stat.lower()

        query = self.stats.find({'guild_id': interaction.guild_id, 'user_id': user.id}).sort(stat, -1)
        data = [entry async for entry in query]

        view = PaginationView(
            f'{stat.title()} Stats',
            data,
            25,
            lambda d: (f'<#{e["channel_id"]}> - **{e[stat]:,}** {stat}' for e in d),
            interaction,
            user.mention + '\n\n',
            user.display_avatar.url
        )

        await interaction.response.send_message(embed=view.embed(), view=view)


    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(stat='The stat to show leaderboard for')
    async def users(self, interaction: Interaction, stat: Stat):
        """Show users leaderboard for the given stat."""

        stat = stat.lower()
        query = self.stats.aggregate([
            {'$match': {'guild_id': interaction.guild_id}},
            {
                '$group': {
                    '_id': '$user_id',
                    'total': {'$sum': f'${stat}'},
                }
            },
            {'$sort': {'total': -1}}
        ])

        data = [entry async for entry in query]

        view = PaginationView(
            f'Users {stat.title()} Leaderboard',
            data,
            25,
            lambda d: (f'<@{e["_id"]}> - **{e["total"]:,}** {stat}' for e in d),
            interaction
        )

        await interaction.response.send_message(embed=view.embed(), view=view)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(channel='The channel to check stats for', stat='The stat to check')
    async def channel(
        self,
        interaction: Interaction,
        channel: discord.TextChannel | discord.VoiceChannel = None,
        stat: Stat = None
    ):
        """Check a channel's stats."""

        channel = channel or interaction.channel
        if stat is None:
            query = self.stats.aggregate([
                {'$match': {'channel_id': channel.id}},
                {
                    '$group': {
                        '_id': '$channel_id',
                        'messages': {'$sum': '$messages'},
                        'words': {'$sum': '$words'},
                        'reactions': {'$sum': '$reactions'},
                        'files': {'$sum': '$files'}
                    }
                }
            ])

            async for entry in query:
                embed = Embed(
                    title='Overall Stats',
                    description=channel.mention
                )
                embed.add_field(name='Messages', value=f'{entry["messages"]:,}', inline=False)
                embed.add_field(name='Words', value=f'{entry["words"]:,}', inline=False)
                embed.add_field(name='Reactions', value=f'{entry["reactions"]:,}', inline=False)
                embed.add_field(name='Files', value=f'{entry["files"]:,}', inline=False)

                return await interaction.response.send_message(embed=embed)

        stat = stat.lower()

        query = self.stats.find({'channel_id': channel.id}).sort(stat, -1)
        data = [entry async for entry in query]

        view = PaginationView(
            f'{stat.title()} Stats',
            data,
            25,
            lambda d: (f'<@{e["user_id"]}> - **{e[stat]:,}** {stat}' for e in d),
            interaction,
            channel.mention + '\n\n'
        )

        await interaction.response.send_message(embed=view.embed(), view=view)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(stat='The stat to show leaderboard for')
    async def channels(self, interaction: Interaction, stat: Stat):
        """Show channels leaderboard for the given stat."""

        stat = stat.lower()
        query = self.stats.aggregate([
            {'$match': {'guild_id': interaction.guild_id}},
            {
                '$group': {
                    '_id': '$channel_id',
                    'total': {'$sum': f'${stat}'},
                }
            },
            {'$sort': {'total': -1}}
        ])

        data = [entry async for entry in query]

        view = PaginationView(
            f'Channels {stat.title()} Leaderboard',
            data,
            25,
            lambda d: (f'<#{e["_id"]}> - **{e["total"]:,}** {stat}' for e in d),
            interaction
        )

        await interaction.response.send_message(embed=view.embed(), view=view)

    @app_commands.command(name='weekly-channel')
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel='The channel to set as the weekly channel')
    async def weekly_channel(self, interaction: Interaction, channel: discord.TextChannel):
        """Set the weekly channel."""

        await self.weekly_channels.update_one(
            {'guild_id': interaction.guild_id},
            {'$set': {'guild_id': interaction.guild_id, 'channel_id': channel.id}},
            upsert=True
        )

        await green_embed(interaction, f'Set the weekly channel to {channel.mention}!')

    @commands.command()
    @is_next()
    @commands.guild_only()
    async def cache_server(self, ctx: Context):
        """Caches the messages in the server."""

        for channel in ctx.guild.channels:
            if isinstance(channel, (discord.CategoryChannel, discord.ForumChannel)):
                continue

            await green_embed(ctx, f'Caching messages stats in {channel.mention}...')

            if await self.stats.find_one({'channel_id': channel.id}) is not None:  # Already cached
                continue

            data: dict[int, ChannelEntry] = defaultdict(
                lambda: ChannelEntry(
                    guild_id=0,
                    channel_id=0,
                    user_id=0,
                    messages=0,
                    words=0,
                    reactions=0,
                    files=0
                )
            )
            async for message in channel.history(limit=None):
                entry = data[message.author.id]
                entry['messages'] += 1
                entry['files'] += len(message.attachments)
                if message.content:
                    entry['words'] += len(message.content.split())

                for reaction in message.reactions:
                    async for user in reaction.users():
                        data[user.id]['reactions'] += 1

            entries = []
            for user_id, entry in data.items():
                entry['guild_id'] = ctx.guild.id
                entry['channel_id'] = channel.id
                entry['user_id'] = user_id
                entries.append(entry)

            if entries:
                await self.stats.insert_many(entries)

        await green_embed(ctx, 'Caching done!', content=ctx.author.mention)

    @loop(time=time(hour=19, minute=0))
    async def weekly_stats(self):
        """Posts the weekly stats on Sundays 19 UTC."""

        await self.bot.wait_until_ready()

        now = discord.utils.utcnow()
        if now.weekday() != 6:
            return

        async for entry in self.weekly_channels.find():
            channel = self.bot.get_channel(entry['channel_id'])
            if channel is None:
                continue

            for stat in ('messages', 'words', 'reactions', 'files'):
                # Channels
                query = self.stats_weekly.aggregate([
                    {'$match': {'guild_id': entry['guild_id']}},
                    {
                        '$group': {
                            '_id': '$channel_id',
                            'total': {'$sum': f'${stat}'},
                        }
                    },
                    {'$sort': {'total': -1}}
                ])

                data = await query.to_list(length=25)

                embed = Embed(
                    title=f'Weekly Channels Leaderboard - {stat.title()}',
                    description='\n'.join(
                        f'{i}. <#{entry["_id"]}> - **{entry["total"]:,}** {stat}'
                        for i, entry in enumerate(data, 1)
                    )
                )

                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    log.warning(f'Couldn\'t send a weekly stats message in the {channel} channel!')

                # Users
                query = self.stats_weekly.aggregate([
                    {'$match': {'guild_id': entry['guild_id']}},
                    {
                        '$group': {
                            '_id': '$user_id',
                            'total': {'$sum': f'${stat}'},
                        }
                    },
                    {'$sort': {'total': -1}}
                ])

                data = await query.to_list(length=25)

                embed = Embed(
                    title=f'Weekly Users Leaderboard - {stat.title()}',
                    description='\n'.join(
                        f'{i}. <@{entry["_id"]}> - **{entry["total"]:,}** {stat}'
                        for i, entry in enumerate(data, 1)
                    )
                )

                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    log.warning(f'Couldn\'t send a weekly stats message in the {channel} channel!')

        await self.stats_weekly.delete_many({})


async def setup(bot: 'NextBot'):
    await bot.add_cog(Stats(bot))
