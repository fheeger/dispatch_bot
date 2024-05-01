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


def read_env_file():
    env = {}
    if os.path.exists(".env"):
        print(".env file found")
        line_nr = 0
        for line in open(".env"):
            if line[0] == "#":
                continue
            line_nr += 1
            key, value = line.strip().split("=")
            env[key] = value
        print("read %i lines from .env file" % line_nr)
    return env


def load_var_from_system(name, default):
    print("loading variable %s from system environment" % name)
    var = os.environ.get(name)
    if var is None:
        print("variable %s not found in system env" % name)
        if default is None:
            raise RuntimeError("%s is not set in .env or as environment variable" % name)
        else:
            print("defaulting to %s for variable %s" % (default, name))
            return default
    else:
        print(f"value: {var}")
        return var


def load_conf_var(name, env, default=None):
    var = env.get(name, None)
    if var is None:
        return load_var_from_system(name, default)
    return var


class Config:
    RED_CATEGORY = "Red"
    BLUE_CATEGORY = "Blue"

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

    TOKEN = None
    BASE_URL = None
    COMMAND_PREFIX = "!"
    DISPATCH_COMMANDS = None

    def __init__(self):
        env = read_env_file()

        self.TOKEN = load_conf_var("TOKEN", env)
        self.BASE_URL = load_conf_var("BASE_URL", env)
        self.COMMAND_PREFIX = load_conf_var("COMMAND_PREFIX", env, self.COMMAND_PREFIX)

        self.DISPATCH_COMMANDS = [
            "%sdispatch" % self.COMMAND_PREFIX,
            "%sDispatch" % self.COMMAND_PREFIX
        ]


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
    await bot.add_cog(MiscCommands(backend, config))
    await bot.add_cog(PlayerCommands(backend, config))
    await bot.add_cog(UmpireCommands(backend, config))
    await bot.add_cog(AdminCommands(backend))
    print("command prefix: {}".format(bot.command_prefix))
    return bot


async def main():
    bot = await setup()
    await bot.start(config.TOKEN)

asyncio.run(main())
