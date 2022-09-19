from discord.ext.commands import Context, check

__all__ = ('is_next',)


def is_next():
    """Checks if the author is next."""

    async def predicate(ctx: Context):
        return ctx.author.id == 342782256001187840

    return check(predicate)
