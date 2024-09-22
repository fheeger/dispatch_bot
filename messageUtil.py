import datetime


def is_new(message, config):
    return not is_older_than(message, config.MISSED_MESSAGE_AGE_LIMIT) and not has_emoji(message, config.SEND_EMOJI)


def is_older_than(message, max_age):
    return datetime.datetime.now(datetime.timezone.utc) - message.created_at > max_age


def has_emoji(message, emoji):
    return any([r.emoji == emoji for r in message.reactions])
