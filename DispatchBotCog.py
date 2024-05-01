from discord.ext import commands


class DispatchBotCog(commands.Cog):
    def __init__(self, backend):
        self.backend = backend

    async def call_game_url(self, ctx, method, url_function, res_id=None, data=None, params=None):
        return self.backend.call(method, url_function, res_id, data, params)

    async def call_account_url(self, ctx, method, url_function, res_id=None, data=None, params=None):
        return self.backend.call(method, url_function, res_id, data, params)
