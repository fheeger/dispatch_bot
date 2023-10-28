import hashlib
import re

from discord.ext import commands

from DispatchBotCog import DispatchBotCog
from Command import Command, NotEnoughArgumentsError
from messageUtil import *
from guildUtils import *
from contextUtils import *


def user_hash(ctx):
    return hashlib.sha256(str(ctx.author.id).encode()).hexdigest()


class UmpireCommands(DispatchBotCog):
    """Umpire Commands"""

    qualified_name = "Umpire Commands"

    def __init__(self, backend, config):
        super().__init__(backend)
        self.config = config


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
            self.config.CREATE_USER_PATH,
            data={"username": username, "discord_user_id_hash": user_hash(ctx)}
        )
        await ctx.send("Account created. Your password will be send to you by DM.")
        await ctx.author.send(
            """A dispatch bot umpire interface account for you has been created. 

            You can login at {}admin
            Your username is {}. Your password is ||{}|| .

            You should change your password once you have logged in for the first time.""".format(
                self.config.BASE_URL,
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
        is_iks = ctx.guild.id == self.config.IKS_SERVER_ID
        if is_iks:
            channels = {c.id: c.name for c in collect_channels(ctx.guild, self.config).values()}
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
                    self.config.GET_ROUND_PATH,
                    params={"server_id": self.config.IKS_SERVER_ID}
                )
                if turn_res['turn'] is not None:
                    await ctx.send("There is already a game running. IKS main server can only run one game at a time.")
                    return
            game_res = await self.call_game_url(ctx, "POST", self.config.NEW_GAME_PATH, data=data)
            if is_iks:
                cat_res = await self.call_game_url(
                    ctx,
                    "POST",
                    "{}{}/".format(self.config.ADD_CATEGORY_PATH, name),
                    data={"category": category_ids},
                    params={"server_id": self.config.IKS_SERVER_ID}
                )
                chnl_res = await self.call_game_url(
                    ctx,
                    "POST",
                    self.config.UPDATE_CHANNELS_PATH,
                    data={"channels": channels},
                    params={"server_id": self.config.IKS_SERVER_ID})
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
        """not). If you do not give any category names, the category, that contains the channel you are typing """ \
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
                "POST",
                "{}{}/".format(self.config.ADD_CATEGORY_PATH, game_name),
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
                "POST",
                "{}{}/".format(self.config.REMOVE_CATEGORY_PATH, game_name),
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
                "{}{}/".format(self.config.LIST_CATEGORIES_PATH, game_name),
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
                "POST",
                self.config.UPDATE_CHANNELS_PATH,
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
                "POST",
                self.config.REMOVE_CHANNEL_PATH,
                data=data,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
            if answer:
                channel_names = get_channel_names_from_ids(ctx, answer["channels"].keys())
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
                self.config.LIST_CHANNEL_PATH,
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
                self.config.CHECK_MESSAGES_PATH,
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
                "POST",
                self.config.NEXT_TURN_PATH,
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
                self.config.GET_MESSAGES_PATH,
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
                               "The server gave the following error:\n%s" % (str(e)[:1000]))
                await ctx.send("\nMessage was from %s and started with %s" % (message["sender"], message["text"][:100]))
            messagesSend += 1
        await ctx.send("%i of %i messages delivered." % (messagesSend, len(messages)))

    @commands.command()
    async def end_game(self, ctx):
        """-> End current game"""
        try:
            res = await self.call_game_url(
                ctx,
                "POST",
                self.config.END_GAME,
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
                self.config.LIST_CHANNEL_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
        except Exception as e:
            await ctx.send("There was an getting channels: %s" % str(e)[:1000])
            raise
        for channel in [ctx.guild.get_channel(r["channel_id"]) for r in response]:
            if channel:
                await ctx.send("Checking channel {} for missed messages".format(channel.name))
                new_messages = 0
                async for message in channel.history(limit=self.config.MESSAGE_HISTORY_LIMIT):
                    if message.content[:9] in self.config.DISPATCH_COMMANDS:
                        if is_new(message, self.config):
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
                                self.config.POST_MESSAGE_PATH,
                                data=data,
                                params={"server_id": ctx.guild.id, "category_id": channel.category_id}
                            )
                            if res is not None:
                                await message.add_reaction(self.config.SEND_EMOJI)
                await ctx.send(" -> Found {} missed messages".format(new_messages))
        await ctx.send("Finished checking for missed messages")

    # @commands.command()
    # async def umpire_time(self, ctx):
    #     """-> Announce to all player channels that it is umpire time now."""
    #     message = "**Umpire time has begun**\n" + \
    #               "You can not give any more orders until next turn, but you can still write dispatches."
    #     await self.broadcast(ctx)
    #     await ctx.send("Umpire time announcement was send")

    @commands.command()
    async def broadcast(self, ctx):
        """-> Send a message to all player channels."""
        message = ctx.message.content.split(None, 1)[1]

        try:
            response = await self.call_game_url(
                ctx,
                "GET",
                self.config.LIST_CHANNEL_PATH,
                params={"server_id": ctx.guild.id, "category_id": ctx.channel.category_id}
            )
        except Exception as e:
            await ctx.send("There was an error getting channels: %s" % str(e)[:1000])
            raise
        send = 0
        for r in response:
            channel = ctx.guild.get_channel(r["channel_id"])
            if channel:
                try:
                    await channel.send(message)
                    send += 1
                except Exception as e:
                    await ctx.send(
                        "There was an error sending broadcast message to %s: %s" % (r["channel_id"], str(e)[:1000])
                    )
                    raise
            else:
                await ctx.send(
                    "There was an error sending broadcast message to %s: Could not find channel" % r["channel_id"]
                )
        await ctx.send("Broadcast send to %i/%i channels." % (send, len(response)))

    @commands.command()
    async def url(self, ctx):
        """-> Reply with current backend URL."""
        await ctx.send("You can reach the backend at: {}admin".format(self.config.BASE_URL))

