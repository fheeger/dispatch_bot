from discord.ext import commands
from requests import HTTPError


class DispatchBotCog(commands.Cog):
    def __init__(self, backend):
        self.backend = backend

    async def call_game_url(self, ctx, method, url_function, res_id=None, data=None, params=None):
        try:
            return self.backend.call(method, url_function, res_id, data, params)
        except HTTPError as e:
            if e.response.status_code == 404:
                await ctx.send("Error finding your game: No game found.\n"
                               "Make sure your categories are set up correctly.")
            elif e.response.status_code == 400:
                await ctx.send("Error finding your game: Multiple games found.\n"
                               "Make sure your categories are set up correctly.")
            elif e.response.status_code == 403:
                await ctx.send("You cannot start a game without creating and account first.\n"
                               "Use the create_account command to do so.")
            elif e.response.status_code == 406:
                await ctx.send("A game with the same name is already going on! Please choose another name")
            else:
                await ctx.send("There was an error calling the server: {}".format(str(e)[:1000]))
            raise e

    async def call_account_url(self, ctx, method, url_function, res_id=None, data=None, params=None):
        try:
            return self.backend.call(method, url_function, res_id, data, params)
        except HTTPError as e:
            if e.response.status_code == 406:
                await ctx.send("ERROR: {}".format(e.response.text))
            else:
                await ctx.send("There was an error calling the server: {}".format(str(e)[:1000]))
            raise e