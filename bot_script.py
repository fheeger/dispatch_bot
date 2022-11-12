import re

import discord
from discord import ChannelType
from discord.ext import commands
from requests import HTTPError

import os

from BackendClient import BackendClient

# read token
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX", "!")
if os.path.exists(".env"):
    for line in open(".env"):
        key, value = line.strip().split("=")
        if TOKEN is None and key == "DISCORD_BOT_TOKEN":
            TOKEN = value
        if key == "COMMAND_PREFIX":
            COMMAND_PREFIX = value


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
UPDATE_CHANNELS_PATH = "bot/update_channels/"
REMOVE_CHANNEL_PATH = "bot/remove_channels/"
LIST_CHANNEL_PATH = "bot/get_channels/"

IKS_SERVER_ID = 769572185005883393
ADMIN_ROLES = []

description = "Dispatch Bot for IKS"
intents = discord.Intents.default()
#intents.members = True


bot = commands.Bot(command_prefix=COMMAND_PREFIX,
                   description=description,
                   intents=intents
                   )
turn = 1


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


def get_channel_ids_from_context(ctx):
    command_array = ctx.message.content.split(" ")
    if len(command_array) > 1:
        return {"channels": [get_channel_by_name(ctx.guild, name).id for name in command_array[1:]]}
    else:
        return {"channels": [ctx.channel.id]}


def get_channels_from_context(ctx):
    command_array = ctx.message.content.split(" ")
    channels = {}
    for name in command_array[1:]:
        channel = get_channel_by_name(ctx.guild, name)
        if channel is None:
            raise AttributeError("Did not find channel with name: {}".format(name))
        channels[channel.id] = name
    if len(command_array) > 1:
        return {"channels": channels}
    else:
        return {"channels": {ctx.channel.id: ctx.channel.name}}


def get_channel_names_from_ids(ctx, ids):
    return [ctx.guild.get_channel(channel_id).name for channel_id in ids]


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print("command prefix: {}".format(bot.command_prefix))
    print("connected to: {}".format(",".join([g.name for g in bot.guilds])))
    print('------')

backend = BackendClient(BASE_URL)


class DispatchBotCog(commands.Cog):
    async def call_url(self, ctx, method, url_function, res_id=None, data=None, params=None):
        try:
            return backend.call(method, url_function, res_id, data, params)
        except HTTPError as e:
            if e.response.status_code == 404:
                await ctx.send("Error finding your game: No game found.\n"
                               "Make sure your categories are set up correctly.")
            elif e.response.status_code == 400:
                await ctx.send("Error finding your game: Multiple games found.\n"
                               "Make sure your categories are set up correctly.")
            elif e.response.status_code == 406:
                await ctx.send("A game with the same name is already going on! Please choose another name")
            else:
                await ctx.send("There was an error calling the server: {}".format(str(e)[:1000]))
            raise e


class MiscCommands(DispatchBotCog):
    """Miscellaneous Commands"""

    qualified_name = "Miscellaneous Commands"

    @commands.command()
    async def hello(self, ctx):
        """-> Say hello"""
        await ctx.send("Hello, I am the TEST DispatchBot")

    @commands.command()
    async def get_round(self, ctx):
        """-> get current round"""
        try:
            res = await self.call_url(
                ctx,
                "GET",
                GET_ROUND_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if res['turn'] is None:
                await ctx.send("There is no game at the moment!")
            else:
                await ctx.send("This is round {} for game {}".format(res['turn'], res['name']))
        except Exception as e:
            await ctx.send("There was an error when fetching the game details: %s" % str(e)[:1000])


class PlayerCommands(DispatchBotCog):
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
            res = await self.call_url(
                ctx,
                "POST",
                POST_MESSAGE_PATH,
                data=data,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if res is not None:
                await ctx.send("Dispatch was send")
        except Exception as e:
            await ctx.send("There was an error sending your dispatch: %s" % str(e)[:1000])

    @commands.command()
    async def Dispatch(self, ctx):
        await self.dispatch(ctx)

    @commands.command()
    async def howto(self, ctx):
        """-> information on how to use the bot as a player."""
        message = open("data/howto_player.txt", "rt").read()
        await ctx.send(message)


class UmpireCommands(DispatchBotCog):
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

        # special case for IKS main server where Red and Blue channels are always added.
        is_iks = ctx.guild.id == IKS_SERVER_ID
        if is_iks:
            channels = {c.id: c.name for c in collect_channels(ctx).values()}
            category_ids = [882564486572167188, 882564565894844426]
        else:
            channels = {}
            category_ids = []

        print(channels)
        data = {
            "channels": {},
            "name_game": name,
            "server_id": ctx.guild.id,
            "user_id": ctx.author.id,
        }

        try:
            if is_iks:
                #is there a game already
                turn_res = await self.call_url(
                    ctx,
                    "GET",
                    GET_ROUND_PATH,
                    params={"server_id": IKS_SERVER_ID}
                )
                if turn_res['turn'] is not None:
                    await ctx.send("There is already a game running. IKS main server can only run one game at a time.")
                    return
            game_res = await self.call_url(ctx, "POST", NEW_GAME_PATH, data=data)
            if is_iks:
                cat_res = await self.call_url(
                    ctx,
                    "PATCH",
                    "{}{}/".format(ADD_CATEGORY_PATH, name),
                    data={"category": category_ids},
                    params={"server_id": IKS_SERVER_ID}
                )
                chnl_res = await self.call_url(
                    ctx,
                    "PATCH",
                    UPDATE_CHANNELS_PATH,
                    data={"channels": channels},
                    params={"server_id": IKS_SERVER_ID})
            else:
                cat_res = True
                chnl_res = True

            if game_res and cat_res and chnl_res:
                message = "Game created\n" \
                          "Name: %s\n" \
                          "Time is now %s\n" \
                          "%i channels" % (game_res["name"], game_res["start_time"], len(channels))
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
        game_name = ctx.message.content.split(" ", 2)[1]
        try:
            category_ids = get_category_ids_from_context(ctx)
        except ValueError as e:
            await ctx.send(str(e))
            return
        try:
            res = await self.call_url(
                ctx,
                "PATCH",
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
            res = await self.call_url(
                ctx,
                "PATCH",
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
            category_ids = await self.call_url(
                ctx,
                "GET",
                "{}{}/".format(LIST_CATEGORIES_PATH, game_name),
                params={"server_id": ctx.guild.id}
            )
        except Exception as e:
            await ctx.send("There was an error listing the categories: %s" % str(e)[:1000])
            raise
        category_names = get_category_names_from_ids(ctx.guild, category_ids)
        await ctx.send("List of categories for game {}\n`    {}`".format(game_name, "\n    ".join(category_names)))


    @commands.command()
    async def add_channel(self, ctx):
        try:
            channels = get_channels_from_context(ctx)
        except AttributeError as e:
            await ctx.send(e.args[0])
            return
        except ValueError as e:
            await ctx.send(str(e))
            return
        try:
            answer = await self.call_url(
                ctx,
                "PATCH",
                UPDATE_CHANNELS_PATH,
                data=channels,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if answer:
                await ctx.send(
                    "The following channels were added or updated in game `{}`: {}".format(
                        answer["game"],
                        ", ".join(answer["channels"].values())
                    )
                )
        except Exception as e:
            await ctx.send("There was an error adding channels: %s" % str(e)[:1000])
            raise

    @commands.command()
    async def remove_channel(self, ctx):
        try:
            channels = get_channel_ids_from_context(ctx)
        except ValueError as e:
            await ctx.send(str(e))
            return
        try:
            answer = await self.call_url(
                ctx,
                "PATCH",
                REMOVE_CHANNEL_PATH,
                data=channels,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if answer:
                channel_names = get_channel_names_from_ids(ctx, answer["channels"])
                await ctx.send(
                    "The following channels were removed from game `{}`: {}".format(
                        answer["game"],
                        ", ".join(channel_names)
                    )
                )
        except Exception as e:
            await ctx.send("There was an error removing channels: %s" % str(e)[:1000])
            raise

    @commands.command()
    async def list_channels(self, ctx):
        try:
            response = await self.call_url(
                ctx,
                "GET",
                LIST_CHANNEL_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
        except Exception as e:
            await ctx.send("There was an error listing channels: %s" % str(e)[:1000])
            raise
        if response:
            channel_names = [channel["name"] for channel in response]
            await ctx.send("List of channels\n`    {}`".format("\n    ".join(channel_names)))

    @commands.command()
    async def next_turn(self, ctx):
        """-> Go to the next turn and deliver all messages for it."""
        try:
            messages = await self.call_url(
                ctx,
                "GET",
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
            res = await self.call_url(
                ctx,
                "PATCH",
                NEXT_TURN_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if 'error' in res:
                await ctx.send("Cannot start the next turn. "+ res['error'])
            else:
                await ctx.send("Next turn started. This is turn {turn}, time is now {current_time}".format(**res))
        except Exception as e:
            await ctx.send("There was an error advancing the turn:%s" % str(e)[:1000])
            raise
        try:
            messages = await self.call_url(
                ctx,
                "GET",
                GET_MESSAGES_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            await ctx.send("Received %i messages from the server" % len(messages))
        except Exception as e:
            await ctx.send("There was an error receiving messages:%s" % str(e)[:1000])
            raise
        messagesSend = 0
        for message in messages:
            try:
                await deliver(ctx.guild, message)
            except Exception as e:
                await ctx.send("There was an error delivering a message."
                               "The server gave the following error:\n%s"% (str(e)[:1000]))
                await ctx.send("\nMessage was from %s and started with %s" % (message["sender"], message["text"][:100]))
            messagesSend += 1
        await ctx.send("%i of %i messages delivered." % (messagesSend, len(messages)))

    @commands.command()
    async def end_game(self, ctx):
        """-> End current game"""
        try:
            res = await self.call_url(
                ctx,
                "PATCH",
                END_GAME,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
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

    @commands.command()
    async def url(self, ctx):
        """-> Reply with current backend URL."""
        await ctx.send("You can reach the backend at: {}admin".format(BASE_URL))


class AdminCommands(DispatchBotCog):
    """Admin Commands"""

    qualified_name = "Admin Commands"

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLES)
    async def message_all(self, ctx, fileName):
        try:
            message = open("data/{}".format(fileName), 'r').read()
        except FileNotFoundError as e:
            await ctx.send("File {} not found.".format(fileName))
            return
        total = len(ctx.guild.members)
        await ctx.send("Will send message to {} server members.".format(total))
        success = 0
        for m, member in enumerate(ctx.guild.members):
            try:
                await member.send(message)
                print("Message send to " + str(member) + " {}/{}".format(m+1, total))
                success += 1
            except:
                print("Message could not be send to " + str(member) + " {}/{}".format(m+1, total))
        await ctx.send("Message was sent to {} out of {} server members.".format(success, total))


bot.add_cog(MiscCommands())
bot.add_cog(PlayerCommands())
bot.add_cog(UmpireCommands())
bot.add_cog(AdminCommands())
bot.run(TOKEN)
