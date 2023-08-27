from discord.ext import commands

from DispatchBotCog import DispatchBotCog
from Command import Command, NotEnoughArgumentsError


class PlayerCommands(DispatchBotCog):
    """Player Commands"""

    qualified_name = "Player Commands"

    def __init__(self, backend, config):
        super().__init__(backend)
        self.config = config

    @commands.command(aliases=["Dispatch"])
    async def dispatch(self, ctx):
        """-> Send everything in the same message as a dispatch"""
        try:
            try:
                command = Command(ctx, 0)
            except NotEnoughArgumentsError as e:
                await ctx.send("Your command did not contain any content.\n"
                               "Write %sdispatch followed by the content of your dispatch in the same discord message."
                               % self.config.COMMAND_PREFIX)
                return
            data = {
                "text": command.args[0],
                "sender": ctx.message.author.display_name
            }
            res = await self.call_game_url(
                ctx,
                "POST",
                self.config.POST_MESSAGE_PATH,
                data=data,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if res is not None:
                await ctx.message.add_reaction(self.config.SEND_EMOJI)
        except Exception as e:
            await ctx.send("There was an error sending your dispatch: %s" % str(e)[:1000])

    @commands.command()
    async def howto(self, ctx):
        """-> Information on how to use the bot as a player."""
        message = open("data/howto_player.txt", "rt").read()
        await ctx.send(message % self.config.COMMAND_PREFIX)


