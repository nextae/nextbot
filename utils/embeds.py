from discord import Embed as DiscordEmbed, TextChannel, VoiceChannel, Interaction, Message, Member, User
from discord.ext.commands import Context

__all__ = (
    'Embed',
    'error_embed',
    'success_embed',
    'green_embed'
)

ValidContext = Context | TextChannel | VoiceChannel | Member | User | Interaction | Message

NEXTBOT_COLOR = 0x9dfd99


class Embed(DiscordEmbed):
    """A custom Embed with the nextbot color already set."""

    def __init__(self, **kwargs):
        super().__init__(color=NEXTBOT_COLOR, **kwargs)


async def error_embed(ctx: ValidContext, text: str, delete_after: int | None = 5, **kwargs) -> Message | None:
    """Sends an error embed."""

    embed = DiscordEmbed(color=0xeb4034, description=f'❌ {text}')

    if isinstance(ctx, Interaction):
        if not ctx.response.is_done():
            return await ctx.response.send_message(embed=embed, **kwargs)
        else:
            return await ctx.followup.send(embed=embed, **kwargs)

    if isinstance(ctx, Message):
        return await ctx.reply(embed=embed, delete_after=delete_after, **kwargs)

    return await ctx.send(embed=embed, delete_after=delete_after, **kwargs)


async def success_embed(ctx: ValidContext, text: str, delete_after: int | None = 5, **kwargs) -> Message | None:
    """Sends a success embed."""

    embed = DiscordEmbed(color=0x32a852, description=f'✅ {text}')

    if isinstance(ctx, Interaction):
        if not ctx.response.is_done():
            return await ctx.response.send_message(embed=embed, **kwargs)
        else:
            return await ctx.followup.send(embed=embed, **kwargs)

    if isinstance(ctx, Message):
        return await ctx.reply(embed=embed, delete_after=delete_after, **kwargs)

    return await ctx.send(embed=embed, delete_after=delete_after, **kwargs)


async def green_embed(ctx: ValidContext, text: str, delete_after: int | None = None, **kwargs) -> Message | None:
    """Sends an embed with the nextbot color."""

    embed = Embed(description=text)

    if isinstance(ctx, Interaction):
        if not ctx.response.is_done():
            return await ctx.response.send_message(embed=embed, **kwargs)
        else:
            return await ctx.followup.send(embed=embed, **kwargs)

    if isinstance(ctx, Message):
        return await ctx.reply(embed=embed, delete_after=delete_after, **kwargs)

    return await ctx.send(embed=embed, delete_after=delete_after, **kwargs)
