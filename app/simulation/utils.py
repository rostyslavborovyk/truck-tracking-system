import datetime


def get_timestamp() -> int:
    return int(datetime.datetime.now().timestamp() * 1000)
