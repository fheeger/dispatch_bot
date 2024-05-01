import traceback

from discord.ext import commands
from requests import HTTPError

from DispatchBotCog import DispatchBotCog
from Command import Command, NotEnoughArgumentsError
from ErrorHandler import GameUrlErrorHandler


class PlayerCommands(DispatchBotCog):
    """Player Commands"""

    qualified_name = "Player Commands"

    def __init__(self, backend, config):
        super().__init__(backend)
        self.config = config

    async def call_dispatch_url(self, ctx, data):
        return self.backend.call("POST", self.config.POST_MESSAGE_PATH, None, data, {"server_id": ctx.guild.id, "category_id": ctx.channel.category_id})

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
            if await self.call_dispatch_url(ctx, data=data):
                await ctx.message.add_reaction(self.config.SEND_EMOJI)
        except Exception as e:
            print(traceback.format_exc())
            await ctx.send("There was an error sending your dispatch: %s" % str(e)[:1000])

    @commands.command()
    async def howto(self, ctx):
        """-> Information on how to use the bot as a player."""
        message = open("data/howto_player.txt", "rt").read()
        await ctx.send(message % self.config.COMMAND_PREFIX)


class DispatchErrorHandler(GameUrlErrorHandler):
    @staticmethod
    async def handle(ctx, error):
        if error.response.status_code == 422:
            await ctx.send(error.response.text.strip("\""))
        else:
            await GameUrlErrorHandler.handle(ctx, error)