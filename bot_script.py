import os
import asyncio
import datetime

import discord

from discord.ext import commands

from BackendClient import BackendClient

from AdminCommands import AdminCommands
from PlayerCommands import PlayerCommands
from UmpireCommands import UmpireCommands
from MiscCommands import MiscCommands


class Config:
    RED_CATEGORY = "Red"
    BLUE_CATEGORY = "Blue"

    BASE_URL = os.environ.get("BASE_URL", "https://django-dispatch-bot.herokuapp.com/")
    CREATE_USER_PATH = "bot/new_user/"
    NEW_GAME_PATH = "bot/new_game/"
    GET_ROUND_PATH = "bot/get_round/"
    NEXT_TURN_PATH = "bot/next_turn/"
    GET_MESSAGES_PATH = "bot/get_messages/"
    CHECK_MESSAGES_PATH = "bot/check_messages/"
    POST_MESSAGE_PATH = "bot/send_message/"
    END_GAME = "bot/end_game/"
    ADD_CATEGORY_PATH = "bot/add_category/"
    REMOVE_CATEGORY_PATH = "bot/remove_category/"
    LIST_CATEGORIES_PATH = "bot/get_categories/"
    UPDATE_CHANNELS_PATH = "bot/update_channels/"
    REMOVE_CHANNEL_PATH = "bot/remove_channels/"
    LIST_CHANNEL_PATH = "bot/get_channels/"

    IKS_SERVER_ID = 769572185005883393
    ADMIN_ROLES = []

    SEND_EMOJI = "📨"
    MESSAGE_HISTORY_LIMIT = 20
    MISSED_MESSAGE_AGE_LIMIT = datetime.timedelta(days=3)

    TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX", "!")

    DISPATCH_COMMANDS = [
        "%sdispatch" % COMMAND_PREFIX,
        "%sDispatch" % COMMAND_PREFIX
    ]

    def __init__(self):
        if os.path.exists(".env"):
            for line in open(".env"):
                key, value = line.strip().split("=")
                if self.TOKEN is None and key == "DISCORD_BOT_TOKEN":
                    self.TOKEN = value
                if key == "COMMAND_PREFIX":
                    self.COMMAND_PREFIX = value


config = Config()
backend = BackendClient(config.BASE_URL)


async def setup():
    description = "Dispatch Bot for IKS"
    intents = discord.Intents.default()
    intents.message_content = True
    print(intents)
    # intents.members = True
    bot = commands.Bot(
        command_prefix=config.COMMAND_PREFIX,
        description=description,
        intents=intents,
        chunk_guilds_at_startup=False
    )

    print("starting...")
    #await bot.add_cog(MiscCommands(backend, config))
    await bot.add_cog(PlayerCommands(backend, config))
    await bot.add_cog(UmpireCommands(backend, config))
    await bot.add_cog(AdminCommands(backend))
    print("command prefix: {}".format(bot.command_prefix))
    return bot


async def main():
    bot = await setup()
    await bot.start(config.TOKEN)

asyncio.run(main())
