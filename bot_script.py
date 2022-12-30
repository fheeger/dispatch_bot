import datetime
import re
import hashlib

import discord
from discord import ChannelType
from discord.ext import commands
from requests import HTTPError

import os

from BackendClient import BackendClient

# read token
from Command import Command, NotEnoughArgumentsError

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
DISPATCH_COMMANDS = [
    "%sdispatch" % COMMAND_PREFIX,
    "%sDispatch" % COMMAND_PREFIX
]

description = "Dispatch Bot for IKS"
intents = discord.Intents.default()
#intents.members = True


bot = commands.Bot(command_prefix=COMMAND_PREFIX,
                   description=description,
                   intents=intents
                   )

def collect_channels(guild):
    channels = {}
    for entry in guild.channels:
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
    for channel in collect_channels(ctx.guild).values():
        await channel.send(message)


def get_category_ids(ctx, category_names):
    category_ids = []
    for name in category_names:
        category = get_channel_by_name(ctx.guild, name)
        if category is None or category.type != ChannelType.category:
            raise ValueError("{} not found or not a category".format(name))
        category_ids.append(category.id)
    return category_ids


def get_category_names_from_ids(server, ids):
    return [server.get_channel(channel_id['number']).name for channel_id in ids]


def get_channel_names_from_ids(ctx, ids):
    return [ctx.guild.get_channel(channel_id).name for channel_id in ids]


def user_hash(ctx):
    return hashlib.sha256(str(ctx.author.id).encode()).hexdigest()


def is_new(message):
    return not is_older_than(message, MISSED_MESSAGE_AGE_LIMIT) and not has_emoji(message, SEND_EMOJI)


def is_older_than(message, max_age):
    return datetime.datetime.now() - message.crreated_at < max_age


def has_emoji(message, emoji):
    return any([r.emoji == emoji for r in message.reactions])


async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print("command prefix: {}".format(bot.command_prefix))
    print("connected to: {}".format(",".join([g.name for g in bot.guilds])))
    print('------')

backend = BackendClient(BASE_URL)


class DispatchBotCog(commands.Cog):
    async def call_game_url(self, ctx, method, url_function, res_id=None, data=None, params=None):
        try:
            return backend.call(method, url_function, res_id, data, params)
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
            return backend.call(method, url_function, res_id, data, params)
        except HTTPError as e:
            if e.response.status_code == 406:
                await ctx.send("ERROR: {}".format(e.response.text))
            else:
                await ctx.send("There was an error calling the server: {}".format(str(e)[:1000]))
            raise e


class MiscCommands(DispatchBotCog):
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
            res = await self.call_game_url(
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

    @commands.command(aliases=["Dispatch"])
    async def dispatch(self, ctx):
        """-> Send everything in the same message as a dispatch"""
        try:
            try:
                command = Command(ctx, 1)
            except NotEnoughArgumentsError as e:
                await ctx.send("Your command did not contain any content.\n"
                               "Write !dispatch followed by the content of your dispatch in the same discord message.")
                return
            data = {
                "text": command.args[0],
                "sender": ctx.message.author.display_name
            }
            res = await self.call_game_url(
                ctx,
                "POST",
                POST_MESSAGE_PATH,
                data=data,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if res is not None:
                await ctx.message.add_reaction(SEND_EMOJI)
        except Exception as e:
            await ctx.send("There was an error sending your dispatch: %s" % str(e)[:1000])

    @commands.command()
    async def howto(self, ctx):
        """-> information on how to use the bot as a player."""
        message = open("data/howto_player.txt", "rt").read()
        await ctx.send(message)

class UmpireCommands(DispatchBotCog):
    """Umpire Commands"""

    qualified_name = "Umpire Commands"

    @commands.command()
    async def create_account(self, ctx):
        """-> Create an account in umpire interface"""
        try:
            command = Command(ctx, 1)
        except NotEnoughArgumentsError:
            await ctx.send("You have to give a username you want to use to login to the umpire interface.")
            return
        username = command.args[0]
        res = await self.call_account_url(
            ctx,
            "POST",
            CREATE_USER_PATH,
            data={"username": username, "discord_user_id_hash": user_hash(ctx)}
        )
        await ctx.send("Account created. Your password will be send to you by DM.")
        await ctx.author.send(
            """A dispatch bot umpire interface account for you has been created. 
            
            You can login at {}/admin
            Your username is {}. Your password is {} .
            
            You should change your password once you have logged in for the first time.""".format(
                BASE_URL,
                username,
                res["password"]
            )
        )

    @commands.command()
    async def start_game(self, ctx):
        """-> Start a new game. The first parameter will be the name of your game."""
        try:
            command = Command(ctx, 1)
        except NotEnoughArgumentsError:
            await ctx.send("You must give a name for your game.")
            return
        name = command.args[0]
        if not re.fullmatch("[0-9A-Za-z-_~]+", name):
            await ctx.send("Your game name can include no spaces and only the following characters: 0-9A-Za-z-_~ .")
            return

        # special case for IKS main server where Red and Blue channels are always added.
        is_iks = ctx.guild.id == IKS_SERVER_ID
        if is_iks:
            channels = {c.id: c.name for c in collect_channels(ctx.guild).values()}
            category_ids = [882564486572167188, 882564565894844426]
        else:
            channels = {}
            category_ids = []

        print(channels)
        data = {
            "channels": {},
            "name_game": name,
            "server_id": ctx.guild.id,
            "user_id": 0,
            "discord_user_id_hash": user_hash(ctx)
        }

        try:
            if is_iks:
                # is there a game already
                turn_res = await self.call_game_url(
                    ctx,
                    "GET",
                    GET_ROUND_PATH,
                    params={"server_id": IKS_SERVER_ID}
                )
                if turn_res['turn'] is not None:
                    await ctx.send("There is already a game running. IKS main server can only run one game at a time.")
                    return
            game_res = await self.call_game_url(ctx, "POST", NEW_GAME_PATH, data=data)
            if is_iks:
                cat_res = await self.call_game_url(
                    ctx,
                    "PATCH",
                    "{}{}/".format(ADD_CATEGORY_PATH, name),
                    data={"category": category_ids},
                    params={"server_id": IKS_SERVER_ID}
                )
                chnl_res = await self.call_game_url(
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
        try:
            command = Command(ctx, 1, arg_num_unlimited=True)
        except NotEnoughArgumentsError:
            await ctx.send("You have to give the name of a game the category should be added to.")
            return
        game_name = command.args[0]
        try:
            if command.arg_num > 1:
                category_ids = get_category_ids(ctx, command.args[1:])
            elif ctx.channel.category_id is None:
                raise ValueError("No names given in message and channel has no category")
            else:
                category_ids = [ctx.channel.category_id]
        except ValueError as e:
            await ctx.send(str(e))
            return
        try:
            res = await self.call_game_url(
                ctx,
                "PATCH",
                "{}{}/".format(ADD_CATEGORY_PATH, game_name),
                data={"category": category_ids},
                params={"server_id": ctx.guild.id}
            )
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
        try:
            command = Command(ctx, 1, arg_num_unlimited=True)
        except NotEnoughArgumentsError:
            await ctx.send("You have to give the name of a game the category should be removed from.")
            return
        game_name = command.args[0]
        try:
            if command.arg_num > 1:
                category_ids = get_category_ids(ctx, command.args[1:])
            elif ctx.channel.category_id is None:
                raise ValueError("No names given in message and channel has no category")
            else:
                category_ids = [ctx.channel.category_id]
        except ValueError as e:
            await ctx.send(str(e))
            return

        try:
            res = await self.call_game_url(
                ctx,
                "PATCH",
                "{}{}/".format(REMOVE_CATEGORY_PATH, game_name),
                data={"category": category_ids},
                params={"server_id": ctx.guild.id}
            )
            await ctx.send("{:n} categories removed from game {}".format(len(category_ids), game_name))
        except Exception as e:
            await ctx.send("There was an error removing the categories: %s" % str(e)[:1000])
            raise


    @commands.command()
    async def list_categories(self, ctx):
        """-> List all categories, that are part of the game."""
        try:
            command = Command(ctx, 1)
        except NotEnoughArgumentsError:
            await ctx.send("You have to give the name of a game to get the list of categories.")
            return
        game_name = command.args[0]
        try:
            category_ids = await self.call_game_url(
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
        """-> Add one or more channels to a game. All other parameters are interpreted as channel names. """ \
            """If you do not give any channel names, the channel, that you are typing in will be added. """ \
            """Channels will be added to game the category they are in is assigned to."""
        command = Command(ctx, 0, arg_num_unlimited=True)
        try:
            channels = {}
            for name in command.args:
                channel = get_channel_by_name(ctx.guild, name)
                if channel is None:
                    raise AttributeError("Did not find channel with name: {}".format(name))
                channels[channel.id] = name
            if command.arg_num > 0:
                data = {"channels": channels}
            else:
                data = {"channels": {ctx.channel.id: ctx.channel.name}}
        except AttributeError as e:
            await ctx.send(e.args[0])
            return
        except ValueError as e:
            await ctx.send(str(e))
            return
        try:
            answer = await self.call_game_url(
                ctx,
                "PATCH",
                UPDATE_CHANNELS_PATH,
                data=data,
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
        """-> Remove one or more channels from a game. All parameters are interpreted as channel names. """ \
            """If you do not give any channel names, the channel, that you are typing in will be removed."""
        command = Command(ctx, 0, arg_num_unlimited=True)
        try:
            channels = {}
            for name in command.args:
                channel = get_channel_by_name(ctx.guild, name)
                if channel is None:
                    raise AttributeError("Did not find channel with name: {}".format(name))
                channels[channel.id] = name
            if command.arg_num > 1:
                data = {"channels": channels}
            else:
                data = {"channels": {ctx.channel.id: ctx.channel.name}}
        except ValueError as e:
            await ctx.send(str(e))
            return
        try:
            answer = await self.call_game_url(
                ctx,
                "PATCH",
                REMOVE_CHANNEL_PATH,
                data=data,
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
        """-> List all channels, that are part of the game."""
        try:
            response = await self.call_game_url(
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
        else:
            await ctx.send("There are no channels in that game.")

    @commands.command()
    async def next_turn(self, ctx):
        """-> Go to the next turn and deliver all messages for it."""
        try:
            messages = await self.call_game_url(
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
            res = await self.call_game_url(
                ctx,
                "PATCH",
                NEXT_TURN_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            await ctx.send("Next turn started. This is turn {turn}, time is now {current_time}".format(**res))
        except Exception as e:
            await ctx.send("There was an error advancing the turn:%s" % str(e)[:1000])
            raise
        try:
            messages = await self.call_game_url(
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
            res = await self.call_game_url(
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
    async def check_for_missed_messages(self, ctx):
        """-> Check for undelivered messages. This is normally unnecessary but can help when the bot was down. """ \
            """Messages that are older than 3 days are ignored."""
        try:
            response = await self.call_game_url(
                ctx,
                "GET",
                LIST_CHANNEL_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
        except Exception as e:
            await ctx.send("There was an getting channels: %s" % str(e)[:1000])
            raise
        for channel in [ctx.guild.get_channel(r["channel_id"]) for r in response]:
            if channel:
                await ctx.send("Checking channel {} for missed messages".format(channel.name))
                new_messages = 0
                async for message in channel.history(limit=MESSAGE_HISTORY_LIMIT):
                    if message.content[:9] in DISPATCH_COMMANDS:
                        if is_new(message):
                            new_messages += 1
                            try:
                                data = {
                                    "text": message.content.split(" ", 1)[1],
                                    "sender": message.author.display_name
                                }
                            except IndexError as e:
                                continue
                            res = await self.call_game_url(
                                ctx,
                                "POST",
                                POST_MESSAGE_PATH,
                                data=data,
                                params={"server_id": ctx.guild.id, "category_id": channel.category_id}
                            )
                            if res is not None:
                                await message.add_reaction(SEND_EMOJI)
                await ctx.send(" -> Found {} missed messages".format(new_messages))
        await ctx.send("Finished checking for missed messages")

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
