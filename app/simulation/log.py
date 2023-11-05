import enum
import typing

from pydantic import BaseModel

from app.simulation.utils import get_timestamp


class LogType(enum.StrEnum):
    TTS_STATE = enum.auto()
    JOURNEY_DISPATCHED = enum.auto()
    JOURNEY_FINISHED = enum.auto()
    TRUCK_NOT_FOUND = enum.auto()

    def __str__(self):
        return str(self.name)


class Log(BaseModel):
    type: LogType
    data: dict[str, typing.Any]
    timestamp: int

    @classmethod
    def create(cls, type: LogType, data: dict[str, typing.Any]):
        return cls(type=type, data=data, timestamp=get_timestamp())
