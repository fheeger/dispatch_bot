class ErrorHandler:
    async def handle(self, ctx, error):
        await ctx.send("There was an error calling the server: {}".format(str(error)[:1000]))
        raise error


class GameUrlErrorHandler(ErrorHandler):
    async def handle(self, ctx, error):
        if error.response.status_code == 404:
            await ctx.send("Error finding your game: No game found.\n"
                           "Make sure your categories are set up correctly.")
        elif error.response.status_code == 400:
            await ctx.send("Error finding your game: Multiple games found.\n"
                           "Make sure your categories are set up correctly.")
        elif error.response.status_code == 403:
            await ctx.send("You cannot start a game without creating and account first.\n"
                           "Use the create_account command to do so.")
        elif error.response.status_code == 406:
            await ctx.send("A game with the same name is already going on! Please choose another name")
        else:
            await super().handle(ctx, error)


class AccountUrlErrorHandler(ErrorHandler):
    async def handle(self, ctx, error):
        if error.response.status_code == 406:
            await ctx.send("ERROR: {}".format(error.response.text))
        else:
            await super().handle(ctx, error)
