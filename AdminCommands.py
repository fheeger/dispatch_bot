from discord.ext import commands
from DispatchBotCog import DispatchBotCog


ADMIN_ROLES = []


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
