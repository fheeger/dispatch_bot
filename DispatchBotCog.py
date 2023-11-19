from discord.ext import commands
from requests import HTTPError

from ErrorHandler import GameUrlErrorHandler, AccountUrlErrorHandler


class DispatchBotCog(commands.Cog):
    def __init__(self, backend):
        self.backend = backend

    async def call_game_url(self, ctx, method, url_function, res_id=None, data=None, params=None):
        try:
            return self.backend.call(method, url_function, res_id, data, params)
        except HTTPError as e:
            await GameUrlErrorHandler().handle(ctx, e)

    async def call_account_url(self, ctx, method, url_function, res_id=None, data=None, params=None):
        try:
            return self.backend.call(method, url_function, res_id, data, params)
        except HTTPError as e:
            await AccountUrlErrorHandler().handle(ctx, e)
