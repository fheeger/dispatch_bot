from discord import ChannelType

from guildUtils import get_channel_by_name


def get_category_ids(ctx, category_names):
    category_ids = []
    for name in category_names:
        category = get_channel_by_name(ctx.guild, name)
        if category is None or category.type != ChannelType.category:
            raise ValueError("{} not found or not a category".format(name))
        category_ids.append(category.id)
    return category_ids


def get_channel_names_from_ids(ctx, ids):
    return [ctx.guild.get_channel(int(channel_id)).name for channel_id in ids]
