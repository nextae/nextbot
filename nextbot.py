from os import getenv

import discord
from aiohttp import ClientSession
from discord import Intents, Game, Emoji
from discord.ext.commands import Bot
from discord.utils import get
from dotenv import load_dotenv
from motor.core import AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient

discord.utils.setup_logging()
load_dotenv()


class NextBot(Bot):
    session: ClientSession
    db: AgnosticDatabase
    extensions: tuple[str] = (
        'cogs.ffz',
        'cogs.help',
        'cogs.misc',
        'cogs.roles',
        'cogs.rsl',
        'cogs.sens',
        'cogs.stats',
        'cogs.twitch',
        'cogs.voice'
    )

    def __init__(self):
        """Initiates the bot and attaches the MongoDB client."""

        super().__init__(
            ['!', '.'],
            intents=Intents.all(),
            activity=Game('nextbot | /help'),
            case_insensitive=True,
            help_command=None
        )

        mongo_client = AsyncIOMotorClient(
            f'mongodb+srv://{getenv("MONGODB_USER")}:{getenv("MONGODB_PASSWORD")}@cluster.sbjxe.mongodb.net'
        )
        self.db = mongo_client['nextbot']

    async def setup_hook(self):
        """Attaches an aiohttp session to the bot and loads the extensions."""

        self.session = ClientSession()
        for ext in self.extensions:
            await self.load_extension(ext)

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
    print(f'-------------------- Bot is ready! --------------------')
    print(f'Logged in as {bot.user}'.center(55))
    print(f'-------------------------------------------------------')


bot.run(getenv('TOKEN'), log_handler=None)
