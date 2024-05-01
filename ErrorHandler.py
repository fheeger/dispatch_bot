from error_type import *


class ErrorHandler:
    @staticmethod
    async def handle(ctx, error):
        await ctx.send("There was an error calling the server: {}".format(str(error)[:1000]))
        raise error


class GameUrlErrorHandler(ErrorHandler):
    @staticmethod
    async def handle(ctx, error):
        if error.error_type == GAME_NOT_FOUND:
            await ctx.send("Error finding your game: No game found.\n"
                           "Make sure your categories are set up correctly.")
        elif error.error_type == GAME_AMBIGUOUS:
            await ctx.send("Error finding your game: Multiple games found.\n"
                           "Make sure your categories are set up correctly.")
        elif error.error_type == NO_ACCOUNT:
            await ctx.send("You cannot start a game without creating and account first.\n"
                           "Use the create_account command to do so.")
        elif error.error_type == GAME_ALREADY_EXISTS:
            await ctx.send("A game with the same name is already going on! Please choose another name")
        else:
            await ErrorHandler.handle(ctx, error)
        raise error


class AccountUrlErrorHandler(ErrorHandler):
    @staticmethod
    async def handle(ctx, error):
        if error.response.status_code == 406:
            await ctx.send("ERROR: {}".format(error.response.text))
        else:
            await ErrorHandler.handle(ctx, error)
        raise error
