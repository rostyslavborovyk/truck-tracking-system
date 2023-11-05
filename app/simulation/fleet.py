import typing

from app.simulation.event import DeliveryRequestEvent
from app.simulation.log import Log, LogType
from app.simulation.truck import Truck


class Fleet:
    def __init__(self, trucks: list[Truck]):
        self.trucks = trucks

    async def select_truck_for_delivery(
        self, event: DeliveryRequestEvent
    ) -> Truck | None:
        def filter_truck(tr: Truck) -> bool:
            return not tr.in_journey and event.load_weight < tr.max_load_weight

        if truck := next(filter(lambda tr: filter_truck(tr), self.trucks), None):
            return truck
        else:
            return None

    def get_info(self) -> dict[str, typing.Any]:
        return {
            "free_trucks": len([tr for tr in self.trucks if not tr.in_journey]),
            "busy_trucks": len([tr for tr in self.trucks if tr.in_journey]),
            "trucks": [tr.get_info() for tr in self.trucks],
        }

    def get_truck_not_found_domain_log(self, event: DeliveryRequestEvent) -> Log:
        return Log.create(
            type=LogType.TRUCK_NOT_FOUND,
            data={
                "origin_address": event.origin_address,
                "destination_address": event.destination_address,
                "load_weight": event.load_weight,
            },
        )
