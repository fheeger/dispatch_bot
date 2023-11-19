from discord import ChannelType


def collect_channels(guild, config):
    channels = {}
    for entry in guild.channels:
        if entry.type == ChannelType.category:
            if entry.name in [config.RED_CATEGORY, config.BLUE_CATEGORY]:
                for channel in entry.text_channels:
                    channels[channel.name] = channel
    return channels


def get_channel_by_name(guild, name):
    for channel in guild.channels:
        if channel.name == name:
            return channel
    return None


async def deliver(guild, message):
    if message["showSender"]:
        dispatch_text = "Dispatch from {sender}:\n>>> {text}".format(**message)
    else:
        dispatch_text = "Dispatch:\n>>> {}".format(message["text"])

    channel = guild.get_channel(message["channelId"])
    if channel is None:
        raise ValueError("Can not find channel {}".format(message["channelName"]))
    await channel.send(dispatch_text)


def get_category_names_from_ids(guild, ids):
    return [guild.get_channel(channel_id['number']).name for channel_id in ids]