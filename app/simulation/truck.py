from __future__ import annotations

import typing

from pydantic import BaseModel

from app.clients.maps import LocationPoint

COLOR_MAP = [
    "#FF0000",
    "#229900",
    "#20cc20",
    "#201cFF",
]

TRUCK_ID = 0


class Truck(BaseModel):
    id: int
    color: str
    location: LocationPoint
    in_journey: bool = False
    max_load_weight: int = 1000

    @classmethod
    def create(cls, location: LocationPoint, max_load_weight: int = 1000) -> Truck:
        global TRUCK_ID
        id_ = TRUCK_ID
        TRUCK_ID += 1
        return cls(
            id=id_,
            color=COLOR_MAP[id_],
            location=location,
            max_load_weight=max_load_weight,
        )

    def get_info(self) -> dict[str, typing.Any]:
        return {
            "id": self.id,
            "in_journey": self.in_journey,
            "location": {
                "lat": self.location.lat,
                "lon": self.location.lon,
            },
        }
