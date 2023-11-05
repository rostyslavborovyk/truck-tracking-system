import os
import typing

from dotenv import load_dotenv

load_dotenv()


def get_or_raise_exception(name: str) -> str:
    if var := os.getenv(name):
        return var
    else:
        raise Exception(f"Unable to get env var {name}")


MAPS_API_TOKEN: typing.Final[str] = get_or_raise_exception("MAPS_API_TOKEN")
TELEGRAM_API_TOKEN: typing.Final[str] = get_or_raise_exception("TELEGRAM_API_TOKEN")
