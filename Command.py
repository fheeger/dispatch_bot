class Command:

    command = None
    arg_num = 0
    args = []

    def __init__(self, ctx, arg_num, arg_num_unlimited=False):
        if arg_num_unlimited:
            arr = ctx.message.content.split(None)
            self.arg_num = len(arr) - 1
        else:
            arr = ctx.message.content.split(None, 1 + arg_num)
            self.arg_num = arg_num
        if len(arr) < arg_num + 1:
            raise NotEnoughArgumentsError
        self.command = arr[0]
        self.args = arr[1:]


class NotEnoughArgumentsError(AttributeError):
    pass
