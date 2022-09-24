from asyncio import run
from logging import basicConfig
from os import getenv

from aiohttp import ClientSession
from discord import Intents, Game, Emoji, Object
from discord.ext.commands import Bot
from discord.utils import get
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

basicConfig(format='[%(asctime)s] [%(levelname)s - %(name)s] %(message)s')
load_dotenv()

GUILD_IDS_TO_SYNC = (479412235115036673, 558697683921928236)


class NextBot(Bot):
    session: ClientSession
    db: AsyncIOMotorDatabase
    extensions: tuple[str] = (
        'cogs.ffz',
        'cogs.help',
        'cogs.misc',
        'cogs.roles',
        'cogs.rsl',
        'cogs.sens',
        'cogs.twitch',
        'cogs.voice'
    )

    def __init__(self):
        """Initiates the bot, removes the default help command and attaches the MongoDB client."""

        super().__init__(['!', '.'], intents=Intents.all(), activity=Game('nextbot | /help'), case_insensitive=True)

        self.remove_command('help')

        mongo_client = AsyncIOMotorClient(
            f'mongodb+srv://{getenv("MONGODB_USER")}:{getenv("MONGODB_PASSWORD")}@cluster.sbjxe.mongodb.net'
        )
        self.db = mongo_client['nextbot']

    async def setup_hook(self):
        """Attaches an aiohttp session to the bot, loads the extensions and syncs the application commands."""

        self.session = ClientSession()
        for ext in self.extensions:
            await self.load_extension(ext)

        for guild_id in GUILD_IDS_TO_SYNC:
            guild = Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def close(self):
        """Closes the aiohttp session and the bot."""

        await self.session.close()
        await super().close()

    def get_emote(self, emote_name: str) -> Emoji | str:
        """Gets an emote with the given name."""

        return get(self.emojis, name=emote_name) or ''


bot = NextBot()


@bot.event
async def on_ready():
    print('----------------------- Bot is ready! -----------------------')


async def main():
    async with bot:
        await bot.start(getenv('TOKEN'))

run(main())
