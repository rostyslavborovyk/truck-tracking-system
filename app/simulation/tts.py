import asyncio
import logging
from typing import Callable

from app.clients.maps import MapsClient
from app.clients.pub_sub import PubSubClient
from app.simulation.event import DeliveryRequestEvent, Event
from app.simulation.fleet import Fleet
from app.simulation.journey import Journey
from app.simulation.log import Log, LogType
from app.simulation.route import Route
from app.simulation.truck import Truck

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TTS:
    def __init__(
        self,
        maps_client: MapsClient,
        pub_sub_client: PubSubClient,
        events_queue: asyncio.Queue[Event],
        fleet: Fleet,
        journeys: list[Journey],
    ):
        self.maps_client = maps_client
        self.pub_sub_client = pub_sub_client
        self.events_queue = events_queue
        self.fleet = fleet
        self.journeys = journeys

        self._journey_finished_queue: asyncio.Queue[Journey] = asyncio.Queue()

    async def run(self):
        logger.info("Starting serving TTS")
        await asyncio.gather(
            *[
                self._listen_events_queue(),
                self._listen_journey_finished_queue(),
                self._log_tts_state(),
                self.pub_sub_client.flush_domain_logs(),
            ]
        )

    async def _listen_events_queue(self):
        while True:
            event = await self.events_queue.get()
            await self.handle_event(event)

    async def _listen_journey_finished_queue(self):
        while True:
            journey = await self._journey_finished_queue.get()
            journey.truck.in_journey = False
            logger.info(f"Finished {journey.get_info()}")
            self.journeys.remove(journey)
            await self.pub_sub_client.add_domain_log(
                journey.get_journey_finished_domain_log()
            )

    async def _log_tts_state(self):
        while True:
            data = {
                "number_of_journeys": len(self.journeys),
                "fleet": self.fleet.get_info(),
            }
            logger.info(f"TTS state: {data}")
            await self.pub_sub_client.add_domain_log(
                Log.create(
                    type=LogType.TTS_STATE,
                    data=data,
                )
            )
            await asyncio.sleep(5)

    async def handle_event(self, event: Event):
        handlers_map: dict[type[Event], Callable] = {
            DeliveryRequestEvent: self._handle_delivery_request,
        }

        if handler := handlers_map.get(event.__class__, None):
            await handler(event)
        else:
            logger.warning("Unknown event", event)

    async def _handle_delivery_request(self, event: DeliveryRequestEvent):
        logger.info(f"Handling delivery request event with id {event.id}")

        if not (truck := await self.fleet.select_truck_for_delivery(event)):
            await self.pub_sub_client.add_domain_log(
                self.fleet.get_truck_not_found_domain_log(event)
            )
            return

        logger.info(f"Found truck {truck.id} for handling event")

        journey = await self._create_journey(event, truck)

        logger.info(f"Created journey {journey.get_info()}")

        await self._serve_journey(journey)

        logger.info(f"Dispatched journey {journey.get_info()}")
        await self.pub_sub_client.add_domain_log(
            journey.get_journey_dispatched_domain_log()
        )

        points = ", ".join([f"{p.lon} {p.lat}" for p in journey.route.location_points])
        await self.pub_sub_client.publish_journey(
            journey_id=journey.id,
            truck_id=truck.id,
            route_geography=f"LINESTRING({points})",
        )

    async def _create_journey(self, event: DeliveryRequestEvent, truck: Truck):
        return Journey.create(
            truck=truck,
            route=Route.from_truck_location_origin_and_destination(
                self.maps_client,
                truck,
                event.origin_address,
                event.destination_address,
            ),
            starting_delay=0,
        )

    async def _serve_journey(self, journey: Journey):
        journey.truck.in_journey = True
        self.journeys.append(journey)
        asyncio.create_task(journey.run(self._journey_finished_queue))
