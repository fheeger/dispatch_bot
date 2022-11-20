# Development
## Setting up you own instance
If you want you can run your own instance of the bot, but in most cases you can just use the existing one.
See *Using the bot* below on how it works.
## Backend
The bot does only work together with a compatible deployment of the [django backend](https://github.com/fheeger/dispatch_bot_backend).
## PyCharm
To run the bot directly from PyCharm you get set the `DISCORD_BOT_TOKEN` environment variable to the bot token in the run configuration.
You might also want to set the `BASE_URL` variable to the URL of your backend or to `localhost:8080` if you are running the backend locally.
## Deployment
Just start the script with the correct environment variables set for `DISCORD_BOT_TOKEN` and `BASE_URL`. 

# Using the bot
## Umpiring
### Basic concept
The umpire sets up a game with the bot.
It is assumed that each player has a personal text channel in which they will receive dispatches.
Players can send dispatches by using the `!dispatch` command.
The messages will show up in the backend where the umpire(s) have to decide to which channel it will be delivered in which turn (or if it will get lost).
Once the umpire starts the next turn all dispatches that are due to be delivered that turn are send to the player channels.
### Adding the bot to your server
Use the [discoed invite link](https://discord.com/api/oauth2/authorize?client_id=897838744458108958&permissions=3072&scope=bot) to add the bot to your game server.
### Starting a game
With the `!start_game <game_name>` command you can start a new game.
The `<game_name>` should be replaced with the name of your game.
The name will be used to identify your game in the further setup.
### Running one or more games per server
The bot is able to handle multiple games per server.
However, this will make the setup a bit more complicated for you as the umpire.
For the players this will make no difference and during the game it will also make no difference for the umpires.
### Adding categories
It is assumed that you use discord categories to organize your game and that each category can only be part of one game. 
This means you have to add categories to your game.
You do this by using the `!add_category` command.
There are two ways to use this command:
 1. `!add_category <game_name>`: This will add the category you are typing in to the game called `game_name`.
 2. `!add_category <game_name> <category_name>`: This will add the category with the name `category_name` to the game called `game_name`. Note: Discord shows category names in caps even if the name is not in all caps.

You need to add all categories in which you have player channels to the game.

### Adding channels
Each channel that is a player channel where you want to send dispatches, needs to be added to the game.
Channels will automatically be added to the game that their category has been added to.
You add channels to a game by using the `!add_channel` command.
There are again two ways to use this command analogous to the `add_category` command:
 1. `!add_channel`: This will add the channel you are typing in to the game that it's category was assigned to.
 2. `!add_channel <channel_name>`: This will add the channel with the name `channel_name` to the game that it's category was assigned to.

If you try to add a channel, that is in a category that was not assigned to a game you will see an error.

Note: If you add a chaneel, that has already been added before it's name will be updated, which can be helpful if you rename channels after starting the game.

### Removing categories and channels
The `!remove_category` and `!remove_channel` commands work analogous to their `add` counterparts.

### Listing categories
With `!list_categories <game_name>` you can list all categories that are part of a game.
### Listing channels
With the `!list_channels` command you can list all the channels of the game that is assigned to the category you are typing in.

### Running the game
Once you have finished resolving a turn you can check in the backend (use `!url` to get the link) for messages that the players have sent.
You can assign messages and turns where and when the messages should arrive, check the **approve** checkbox and click the **Save** button.
After that let the dispatch bot know you want to move to the next turn by using the `!next_turn` command in a channel that is part of the game.

### Renaming channels
If you rename a channel during the game, the bot will still work (because it uses channel IDs under the hood),
but in the umpire interface the channel name will still be the old name.
To update it, you can add the channel to the game again.