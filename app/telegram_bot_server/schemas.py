import typing

from pydantic import BaseModel


class Notification(BaseModel):
    event_type: str
    additional_data: dict[str, typing.Any]
