import re

from discord import ChannelType
from discord.ext import commands
import requests
import json
import os

# read token
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if TOKEN is None and os.path.exists(".env"):
    for line in open(".env"):
        key, value = line.strip().split("=")
        if key == "DISCORD_BOT_TOKEN":
            TOKEN = value


RED_CATEGORY = "Red"
BLUE_CATEGORY = "Blue"

BASE_URL = os.environ.get("BASE_URL", "https://django-dispatch-bot.herokuapp.com/")
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


description = "Dispatch Bot for IKS"
bot = commands.Bot(command_prefix='!',
                   description=description,
                   )
turn = 1

headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}


def get_url(url_function, res_id=None, params=None):
    """ general function get to read"""
    this_url = BASE_URL + url_function
    if res_id is not None:
        this_url += '/' + str(res_id)
    response = requests.get(this_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def patch_url(url_function, res_id=None, data=None, params=None):
    """ general function put to update"""
    url = BASE_URL + url_function
    if res_id:
        url += str(res_id)
    if data:
        data = json.dumps(data)
    response = requests.patch(url, data=data, headers=headers, params=params)
    return response.json()


def post_url(url_function, data=None, params=None):
    """ general function post to create"""
    url = BASE_URL + url_function
    response = requests.post(url, data=json.dumps(data), headers=headers, params=params)
    return response.json()


def collect_channels(ctx):
    channels = {}
    for entry in ctx.guild.channels:
        if entry.type == ChannelType.category:
            if entry.name in [RED_CATEGORY, BLUE_CATEGORY]:
                for channel in entry.text_channels:
                    channels[channel.name] = channel
    return channels


def get_channel_by_name(srv, name):
    for chnl in srv.channels:
        if chnl.name == name:
            return chnl
    return None


async def deliver(srv, message):
    dispatch_text = "Dispatch from %s:\n>>> %s" % (message["sender"], message["text"])
    channel = get_channel_by_name(srv, message["channelName"])
    if channel is None:
        raise ValueError("Can not find channel {}".format(message["channelName"]))
    await channel.send(dispatch_text)


async def broadcast(ctx, message):
    for channel in collect_channels(ctx).values():
        await channel.send(message)


def get_category_ids(ctx, category_names):
    category_ids = []
    for name in category_names:
        category = get_channel_by_name(ctx.guild, name)
        if category is None or category.type != ChannelType.category:
            raise ValueError("{} not found or not a category".format(name))
        category_ids.append(category.id)
    return category_ids


def get_category_ids_from_context(ctx):
    command_array = ctx.message.content.split(" ")
    if len(command_array) > 2:
        return get_category_ids(ctx, command_array[2:])
    elif ctx.channel.category_id is None:
        raise ValueError("No names given in message and channel has no category")
    else:
        return [ctx.channel.category_id]


def get_category_names_from_ids(server, ids):
    return [server.get_channel(channel_id['number']).name for channel_id in ids]


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


class MiscCommands(commands.Cog):
    """Miscellaneous Commands"""

    qualified_name = "Miscellaneous Commands"

    @commands.command()
    async def hello(self, ctx):
        """-> Say hello"""
        await ctx.send("Hello, I am the DispatchBot")

    @commands.command()
    async def get_round(self, ctx):
        """-> get current round"""
        try:
            res = get_url(GET_ROUND_PATH, params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id})
            if res['turn'] is None:
                await ctx.send("There is no game at the moment!")
            else:
                await ctx.send("This is round {} for game {}".format(res['turn'], res['name']))
        except Exception as e:
            await ctx.send("There was an error when fetching the game details: %s" % str(e)[:1000])


class PlayerCommands(commands.Cog):
    """Player Commands"""

    qualified_name = "Player Commands"

    @commands.command()
    async def dispatch(self, ctx):
        """-> Send everything in the same message as a dispatch"""
        try:
            try:
                data = {
                    "text": ctx.message.content.split(" ", 1)[1],
                    "sender": ctx.message.author.display_name
                }
            except IndexError as e:
                await ctx.send("Your command did not contain any content.\n"
                               "Write !dispatch followed by the content of your dispatch in the same discord message.")
                return
            res = post_url(
                POST_MESSAGE_PATH,
                data,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if 'error' in res:
                await ctx.send("Dispatch could not be send: %s" % res['error'][:1000])
            else:
                await ctx.send("Dispatch was send")
        except Exception as e:
            await ctx.send("There was an error sending your dispatch: %s" % str(e)[:1000])

    @commands.command()
    async def Dispatch(self, ctx):
        await self.dispatch(ctx)


class UmpireCommands(commands.Cog):
    """Umpire Commands"""

    qualified_name = "Umpire Commands"

    @commands.command()
    async def start_game(self, ctx):
        """-> Start a new game. The first parameter will be the name of your game."""
        if ctx.message.content.count(" ") < 1:
            await ctx.send("You must give a name for your game.")
            return
        name = ctx.message.content.split(" ", 1)[1]
        if not re.fullmatch("[0-9A-Za-z-_~]+", name):
            await ctx.send("Your game name can include no spaces and only the following characters: 0-9A-Za-z-_~ .")
            return
        channels = collect_channels(ctx)

        print(channels)
        data = {
            "name_channels": list(channels.keys()),
            "name_game": name,
            "server_id": ctx.guild.id,
            "user_id": ctx.author.id,
        }
        try:
            res = post_url(NEW_GAME_PATH, data)
            if 'error' in res:
                await ctx.send(res['error'])
            else:
                message = "Game created\n" \
                          "Name: %s\n" \
                          "Time is now %s\n" \
                          "%i channels" % (res["name"], res["start_time"], len(channels))
                await ctx.send(message)
        except Exception as e:
            await ctx.send("There was an error creating the game:%s" % str(e)[:1000])
            raise

    @commands.command()
    async def add_category(self, ctx):
        """-> Add one or more categories to a game. First parameter is the game name, all other parameters are """ \
            """interpreted as category names (remember that discord shows category names in caps even if the are """ \
            """not). If you do not give any category names, the category, that contains the channel you are typing """\
            """in will be added."""
        if ctx.message.content.count(" ") < 1:
            await ctx.send("You have to give the name of a game the category should be added to.")
            return
        game_name = ctx.message.content.split(" ", 1)[1]
        try:
            category_ids = get_category_ids_from_context(ctx)
        except ValueError as e:
            await ctx.send(str(e))
            return
        try:
            res = patch_url(
                "{}{}/".format(ADD_CATEGORY_PATH, game_name),
                data={"category": category_ids},
                params={"server_id": ctx.guild.id}
            )
            if 'error' in res:
                await ctx.send(res['error'])
            else:
                await ctx.send("{:n} categories added to game {}".format(len(category_ids), game_name))
        except Exception as e:
            await ctx.send("There was an error adding the categories: %s" % str(e)[:1000])
            raise


    @commands.command()
    async def remove_category(self, ctx):
        """-> Remove one or more categories from a game. First parameter is the game name, all other parameters """ \
            """are interpreted as category names (remember that discord shows category names in caps even if the """ \
            """are not). If you do not give any category names, the category, that contains the channel you are """ \
            """typing in will be removed."""
        if ctx.message.content.count(" ") < 1:
            await ctx.send("You have to give the name of a game the category should be removed from.")
            return
        game_name = ctx.message.content.split(" ", 2)[1]
        try:
            category_ids = get_category_ids_from_context(ctx)
        except ValueError as e:
            await ctx.send(str(e))
            return

        try:
            res = patch_url(
                "{}{}/".format(REMOVE_CATEGORY_PATH, game_name),
                data={"category": category_ids},
                params={"server_id": ctx.guild.id}
            )
            if 'error' in res:
                await ctx.send(res['error'])
            else:
                await ctx.send("{:n} categories removed from game {}".format(len(category_ids), game_name))
        except Exception as e:
            await ctx.send("There was an error removing the categories: %s" % str(e)[:1000])
            raise


    @commands.command()
    async def list_categories(self, ctx):
        """-> List all categories, that are part of the game."""
        if ctx.message.content.count(" ") < 1:
            await ctx.send("You have to give the name of a game to get the list of categories.")
            return
        game_name = ctx.message.content.split(" ", 2)[1]
        try:
            category_ids = get_url(
                "{}{}/".format(LIST_CATEGORIES_PATH, game_name),
                params={"server_id": ctx.guild.id}
            )
            category_names = get_category_names_from_ids(ctx.guild, category_ids)
            await ctx.send("List of categories for game {}\n`    {}`".format(game_name, "\n    ".join(category_names)))
        except Exception as e:
            await ctx.send("There was an error listing the categories: %s" % str(e)[:1000])
            raise


    @commands.command()
    async def next_turn(self, ctx):
        """-> Go to the next turn and deliver all messages for it."""
        try:
            messages = get_url(
                CHECK_MESSAGES_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if len(messages) > 0:
                error = "Warning : there are still %i messages on the server that are not approved.\n" % len(messages)
                await ctx.send(error)
        except Exception as e:
            await ctx.send("There was an error checking the messages:%s" % str(e)[:1000])
            raise
        try:
            res = patch_url(NEXT_TURN_PATH, params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id})
            if 'error' in res:
                await ctx.send("Cannot start the next turn. "+ res['error'])
            else:
                await ctx.send("Next turn started. This is turn {turn}, time is now {current_time}".format(**res))
        except Exception as e:
            await ctx.send("There was an error advancing the turn:%s" % str(e)[:1000])
            raise
        try:
            messages = get_url(
                GET_MESSAGES_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            await ctx.send("Received %i messages from the server" % len(messages))
        except Exception as e:
            await ctx.send("There was an error receiving messages:%s" % str(e)[:1000])
            raise
        try:
            for message in messages:
                await deliver(ctx.guild, message)
        except Exception as e:
            await ctx.send("There was an error delivering messages:%s" % str(e)[:1000])
            raise

    @commands.command()
    async def end_game(self, ctx):
        """-> End current game"""
        try:
            res = patch_url(END_GAME, params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id})
            if 'error' in res:
                await ctx.send(res['error'])
            else:
                await ctx.send("The following game has been ended : %s at turn %i" % (res['name'], res['turn']))
        except Exception as e:
            await ctx.send("There was an error ending the game:%s" % str(e)[:1000])
            raise

    @commands.command()
    async def umpire_time(self, ctx):
        """-> Announce to all player channels that it is umpire time now."""
        message = "**Umpire time has begun**\n" + \
                  "You can not give any more orders until next turn, but you can still write dispatches."
        await broadcast(ctx, message)
        await ctx.send("Umpire time announcement was send")

    @commands.command()
    async def broadcast(self, ctx):
        """-> Send a message to all player channels."""
        await broadcast(ctx, ctx.message.content.split(" ", 1)[1])
        await ctx.send("Broadcast was send")


bot.add_cog(MiscCommands())
bot.add_cog(PlayerCommands())
bot.add_cog(UmpireCommands())
bot.run(TOKEN)
