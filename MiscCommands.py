from discord.ext import commands

from DispatchBotCog import DispatchBotCog


class MiscCommands(DispatchBotCog):
    """Miscellaneous Commands"""

    qualified_name = "Miscellaneous Commands"

    def __init__(self, backend, config):
        super().__init__(backend)
        self.config = config

    @commands.command()
    async def hello(self, ctx):
        """-> Say hello"""
        await ctx.send("Hello, I am the DispatchBot")

    #@commands.command()
    async def get_round(self, ctx):
        """-> get current round"""
        try:
            res = await self.call_game_url(
                ctx,
                "GET",
                self.config.GET_ROUND_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if res['turn'] is None:
                await ctx.send("There is no game at the moment!")
            else:
                await ctx.send("This is round {} for game {}".format(res['turn'], res['name']))
        except Exception as e:
            await ctx.send("There was an error when fetching the game details: %s" % str(e)[:1000])

