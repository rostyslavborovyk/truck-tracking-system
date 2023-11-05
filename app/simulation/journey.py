import asyncio
import logging
import random

from app.simulation.log import Log, LogType
from app.simulation.route import Route
from app.simulation.truck import Truck

JOURNEY_ID = 0

logger = logging.getLogger(__name__)


class Journey:
    def __init__(
        self,
        truck: Truck,
        route: Route,
        starting_delay: float = 0,
    ):
        global JOURNEY_ID
        self.id = JOURNEY_ID
        JOURNEY_ID += 1
        self.truck = truck
        self.route = route
        self.starting_delay = starting_delay
        self._progress_percentage = 0.0
        self._delay = 0.05

    @classmethod
    def create(
        cls,
        truck: Truck,
        route: Route,
        starting_delay: float,
    ):
        return cls(
            truck=truck,
            route=route,
            starting_delay=starting_delay,
        )

    async def run(self, journey_finished_events: asyncio.Queue):
        await asyncio.sleep(self.starting_delay)
        for i, lp in enumerate(self.route.location_points):
            self.truck.location = lp
            self._progress_percentage = (i + 1) / len(self.route.location_points) * 100
            # await self._log_movement()
            await asyncio.sleep(self._delay + self._get_jitter())

        await journey_finished_events.put(self)

    def get_info(self):
        return (
            f"Journey info: Truck id: {self.truck.id}, "
            f"from {self.route.origin_address}, to {self.route.destination_address}"
        )

    def get_journey_dispatched_domain_log(self):
        return Log.create(
            type=LogType.JOURNEY_DISPATCHED,
            data={
                "journey_id": self.id,
                "truck_id": self.truck.id,
                "origin_address": self.route.origin_address,
                "destination_address": self.route.destination_address,
                "expected_duration_in_seconds": self.route.expected_duration_in_seconds,
                "route_lines": self.route.location_points,
            },
        )

    def get_journey_finished_domain_log(self):
        return Log.create(
            type=LogType.JOURNEY_FINISHED,
            data={
                "journey_id": self.id,
                "truck_id": self.truck.id,
                "origin_address": self.route.origin_address,
                "destination_address": self.route.destination_address,
            },
        )

    def _get_jitter(self) -> float:
        """
        Returns a random value to normalize the distribution of delay for cars
        """
        return random.random() * self._delay / 10

    async def _log_movement(self):
        logger.info(
            f"Truck with id {self.truck.id} "
            f"on the location point {self.truck.location.lat} {self.truck.location.lon} "
            f"progress {self._progress_percentage:.2f}%"
        )
        #
        # await self.pub_sub_client.publish_events(
        #     [
        #         JourneyTrackEvent(
        #             truck_id=self.truck.id,
        #             lat=self.truck.location.lat,
        #             lon=self.truck.location.lon,
        #             timestamp=get_timestamp(),
        #             color=self.truck.color,
        #         )
        #     ]
        # )
