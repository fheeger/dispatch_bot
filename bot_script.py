from discord import ChannelType
from discord.ext import commands
import requests
import json
import os

# read token
TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

RED_CATEGORY = "Red"
BLUE_CATEGORY = "Blue"

BASE_URL = 'https://django-dispatch-bot.herokuapp.com/'
NEW_GAME_PATH = "bot/new_game/"
GET_ROUND_PATH = "bot/get_round/"
NEXT_TURN_PATH = "bot/next_turn/"
GET_MESSAGES_PATH = "bot/get_messages/"
CHECK_MESSAGES_PATH = "bot/check_messages/"
POST_MESSAGE_PATH = "bot/send_message/"
END_GAME = "bot/end_game/"


description = "Dispatch Bot for IKS"
bot = commands.Bot(command_prefix='!',
                   description=description,
                   )
turn = 1

headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}


def get_url(url_function, id=None, filter=None):
    """ general function get to read"""
    this_url = BASE_URL + url_function
    if id is not None:
        this_url += '/' + str(id)
    response = requests.get(this_url, params=filter, headers=headers)
    response.raise_for_status()
    return response.json()


def patch_url(url_function, id=None, data=None):
    """ general function put to update"""
    url = BASE_URL + url_function
    if id:
        url += str(id)
    if data:
        data = json.dumps(data)
    response = requests.patch(url, data=data, headers=headers)
    return response.json()


def post_url(url_function, data=None):
    """ general function post to create"""
    url = BASE_URL + url_function
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()


def get_channel_by_name(name):
    srv = bot.guilds[0]  # TODO make generic
    for chnl in srv.channels:
        if chnl.name == name:
            return chnl
    return None


async def deliver(message):
    dispatch_text = "Dispatch from %s:\n>>> %s" % (message["sender"], message["text"])
    channel = get_channel_by_name(message["channelName"])
    await channel.send(dispatch_text)


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
            res = get_url(GET_ROUND_PATH)
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
            res = post_url(POST_MESSAGE_PATH, data)
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
    async def start_game(self, ctx, name: str):
        """-> Start a new game."""
        blue = {}
        red = {}
        for entry in ctx.guild.channels:
            if entry.type == ChannelType.category:
                if entry.name == RED_CATEGORY:
                    for channel in entry.text_channels:
                        red[channel.name] = channel.id
                if entry.name == BLUE_CATEGORY:
                    for channel in entry.text_channels:
                        blue[channel.name] = channel.id

        print(red)
        print(blue)
        data = {
            "name_channels": list(blue.keys()) + list(red.keys()),
            "name_game": name
        }
        try:
            res = post_url(NEW_GAME_PATH, data)
            if 'error' in res:
                await ctx.send(res['error'])
            else:
                message = "Game created\n" \
                          "Name: %s\n" \
                          "Time is now %s\n" \
                          "%i Blue channels\n" \
                          "%i Red channels" % (res["name"], res["start_time"], len(blue), len(red))
                await ctx.send(message)
        except Exception as e:
            await ctx.send("There was an error creating the game:%s" % str(e)[:1000])
            raise

    @commands.command()
    async def next_turn(self, ctx):
        """-> Go to the next turn and deliver all messages for it."""
        try:
            messages = get_url(CHECK_MESSAGES_PATH)
            if len(messages) > 0:
                error = "Warning : there are still %i messages on the server that are not approved.\n" % len(messages)
                await ctx.send(error)
        except Exception as e:
            await ctx.send("There was an error checking the messages:%s" % str(e)[:1000])
            raise
        try:
            res = patch_url(NEXT_TURN_PATH)
            if 'error' in res:
                await ctx.send("Cannot start the next run. "+ res['error'])
            else:
                await ctx.send("Next turn started. This is turn {turn}, time is now {current_time}".format(**res))
        except Exception as e:
            await ctx.send("There was an error advancing the turn:%s" % str(e)[:1000])
            raise
        try:
            messages = get_url(GET_MESSAGES_PATH)
            await ctx.send("Received %i messages from the server" % len(messages))
        except Exception as e:
            await ctx.send("There was an error receiving messages:%s" % str(e)[:1000])
            raise
        try:
            for message in messages:
                await deliver(message)
        except Exception as e:
            await ctx.send("There was an error delivering messages:%s" % str(e)[:1000])
            raise

    @commands.command()
    async def end_game(self, ctx):
        """-> End current game"""
        try:
            res = patch_url(END_GAME)
            if 'error' in res:
                await ctx.send(res['error'])
            else:
                await ctx.send("The following game has been ended : %s at turn %i" % (res['name'], res['turn']))
        except Exception as e:
            await ctx.send("There was an error ending the game:%s" % str(e)[:1000])
            raise


bot.add_cog(MiscCommands())
bot.add_cog(PlayerCommands())
bot.add_cog(UmpireCommands())
bot.run(TOKEN)
