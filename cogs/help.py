from typing import TYPE_CHECKING

from discord import ButtonStyle, Interaction
from discord.app_commands import command
from discord.ext.commands import Cog
from discord.ui import View, Button, button

from utils.embeds import Embed

if TYPE_CHECKING:
    from nextbot import NextBot

COMMANDS_DESCRIPTIONS = {
    'misc': [
        ('/math <a> <sign> <b>', 'Calculates simple operations.', '/math 5 * 7'),
        (
            '/numbersystemconverter <input_base> <output_base> <number>',
            'Converts `<number>` from number system of `<input_base>` to a `<output_base>` number system.',
            '/nsc 2 10 101101'
        ),
        (
            '/sens <game> <sens> <dpi>',
            'Calculates your cm / 360°.',
            '/sens Overwatch 4.5 800'
        ),
        (
            '/convert <game1> <game2> <sens>',
            'Converts your sensitivity from `<game1>` to `<game2>`',
            '/convert Overwatch Spellbreak 4.5'
        )
    ],
    'twitch': [
        (
            '/twitch notify <twitch_user> [channel] [message]',
            'Sets up a notification when `<twitch_user>` goes live on Twitch with a `[message]` '
            '(use `<mention>` where you want to be mentioned).\n'
            'The notification will be sent to `[channel]` or leave it empty to get the notification in DMs',
            '/twitch notify #twitch xqc <mention> xQc went live PogU!'
        ),
        (
            '/twitch edit <twitch_user> [channel] [message]',
            'Edits the notification message and/or channel for `<twitch_user>`.',
            '/twitch edit xqc <mention> Wowzers my juicer went live!'
        ),
        ('/twitch remove <twitch_user>', 'Removes the notification for `<twitch_user>`.', '/twitch remove xqc'),
        (
            '/twitch streams <game>',
            'Shows 5 most watched Twitch streams that are streaming `<game>`.',
            '/twitch streams Spellbreak'
        )
    ],
    'ffz': [
        (
            '/ffz <query> [number] [random]',
            'Sends an emote from FrankerFaceZ. Options: either a number of which emote in order or random',
            '/ffz PagMan 3'
        ),
        ('/upload <query> [number] [random]', 'Same as `/ffz` but lets you upload the emote.', '/upload Pepega')
    ],
    'reaction_roles': [
        (
            '/reactionroles setup <channel>',
            'Sets up Reaction Roles in the mentioned channel.',
            '/reactionroles setup #roles'
        ),
        ('/reactionroles add', 'Creates a new role and adds it to Reaction Roles.', None),
        (
            '/reactionroles remove <role>',
            'Removes a role from the server and Reaction Roles',
            '/reactionroles remove Valorant'
        ),
        ('/reactionroles reset', 'Completely resets Reaction Roles', None)
    ],
    'voice': [
        (
            '/play <query>',
            'Plays a query/link from YouTube or adds it to the queue.',
            '/p https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        ),
        ('/tts <query>', 'Plays a TTS message or adds it to the queue.', '/tts hello my name is Brian'),
        (
            '/ttschannel <channel> <query>',
            'Plays a TTS message in the specified channel or adds it to the queue.',
            '/tc Music how are you today guys?'
        ),
        ('/pause', 'Pauses the currently playing audio.', None),
        ('/resume', 'Resumes the currently paused audio.', None),
        ('/skip', 'Skips the currently playing audio and plays the next one from the queue', None),
        ('/queue', 'Shows the queue.', None),
        ('/remove <number>', 'Removes an entry from the queue.', '/remove 3'),
        ('/volume [volume]', 'Displays the current audio volume or changes it (0 - 100).', '/volume 50'),
        ('/loop', 'Enables or disables the queue loop.', None),
        ('/join', 'Makes the bot join your voice channel.', None),
        ('/leave', 'Makes the bot leave the voice channel and removes the queue.', None),
        ('/stop', 'Stops any audio playing and removes the queue.', None)
    ]
}

TITLES = {
    'misc': 'Miscellaneous',
    'twitch': 'Twitch',
    'ffz': 'FFZ',
    'reaction_roles': 'Reaction Roles',
    'voice': 'Voice'
}


def create_help_embed(category: str) -> Embed:
    """Creates a help embed."""

    return Embed(title=TITLES[category], description=create_help_embed_description(category))


def create_help_embed_description(category: str) -> str:
    """Creates a description for the help embed."""

    description = ''
    for usage, command_description, example in COMMANDS_DESCRIPTIONS[category]:
        if example is not None:
            description += f'```{usage}```**{command_description}**\nExample: `{example}`\n\n'
        else:
            description += f'```{usage}```**{command_description}**\n\n'

    return description


class HelpView(View):
    embeds = {category: create_help_embed(category) for category in COMMANDS_DESCRIPTIONS}

    def __init__(self):
        super().__init__(timeout=None)
        self.current_page = 'misc'
        self.misc.disabled = True

    @button(label='Misc', style=ButtonStyle.grey, emoji='<:misc:926153284488671253>')
    async def misc(self, interaction: Interaction, btn: Button):
        """Displays the Miscellaneous help page."""

        btn.disabled = True
        getattr(self, self.current_page).disabled = False
        self.current_page = 'misc'

        await interaction.response.edit_message(embed=self.embeds['misc'], view=self)

    @button(label='Twitch', style=ButtonStyle.grey, emoji='<:twitch:926151423383707658>')
    async def twitch(self, interaction: Interaction, btn: Button):
        """Displays the Twitch help page."""

        btn.disabled = True
        getattr(self, self.current_page).disabled = False
        self.current_page = 'twitch'

        await interaction.response.edit_message(embed=self.embeds['twitch'], view=self)

    @button(label='FFZ', style=ButtonStyle.grey, emoji='<:ffz:926150575857479750>')
    async def ffz(self, interaction: Interaction, btn: Button):
        """Displays the FFZ help page."""

        btn.disabled = True
        getattr(self, self.current_page).disabled = False
        self.current_page = 'ffz'

        await interaction.response.edit_message(embed=self.embeds['ffz'], view=self)

    @button(label='Reaction Roles', style=ButtonStyle.grey, emoji='<:reaction_roles:926152364015120394>')
    async def reaction_roles(self, interaction: Interaction, btn: Button):
        """Displays the Reaction Roles help page."""

        btn.disabled = True
        getattr(self, self.current_page).disabled = False
        self.current_page = 'reaction_roles'

        await interaction.response.edit_message(embed=self.embeds['reaction_roles'], view=self)

    @button(label='Voice', style=ButtonStyle.grey, emoji='<:voice:926152363922829382>')
    async def voice(self, interaction: Interaction, btn: Button):
        """Displays the Voice help page."""

        btn.disabled = True
        getattr(self, self.current_page).disabled = False
        self.current_page = 'voice'

        await interaction.response.edit_message(embed=self.embeds['voice'], view=self)


class Help(Cog):
    bot: 'NextBot'

    def __init__(self, bot: 'NextBot'):
        self.bot = bot

    @command()
    async def help(self, interaction: Interaction):
        """Shows help and information about the commands."""

        await interaction.response.send_message(embed=HelpView.embeds['misc'], view=HelpView())


async def setup(bot: 'NextBot'):
    await bot.add_cog(Help(bot))
