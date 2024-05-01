import os

import discord


class TestClient:
    TOKEN = os.environ.get("TEST_BOT_TOKEN")
    TEST_SERVER_ID = 0

    intents = discord.Intents.default()
    intents.members = True

    client = discord.Client(intents=intents)

    message_dump = []

    channel_struct = {
        "bot_test_blue": [
            "blue-1-Clausewitz",
            "blue-2-Bluecher",
            "blue-3-Dessau"
        ],
        "bot_test_red": [
            "red-2-Vaubaun",
            "red-1-Turenne",
            "red-1-Murat"
        ]
    }
    channels = {}
    categories = {}
    umpire_channel = {}

    @client.event
    async def on_ready(self):
        print(f"We have logged in as {self.client.user}")

    @client.event
    async def on_message(self, message):
        if message.author == self.client.user:
            return

        self.message_dump.append(message)

    async def get_server(self):
        return self.client.get_guild(self.TEST_SERVER_ID)

    async def setup_channels(self):
        server = await self.get_server()
        for catName, channelNames in self.channel_struct.items():
            cat = await server.create_category(catName)
            self.categories[catName] = cat
            for chnName in channelNames:
                self.channels[chnName] = await server.creat_text_channel(chnName, reason=None, category=cat)

        self.umpire_channel = server.creat_text_channel("umpires")

    def run(self):
        self.client.run(self.TOKEN)
