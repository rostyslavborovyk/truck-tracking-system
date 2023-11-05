import asyncio

from app.clients.maps import LocationPoint, MapsClient
from app.clients.pub_sub import PubSubClient
from app.simulation.event import DeliveryRequestEvent, Event
from app.simulation.journey import Journey
from app.simulation.route import Route
from app.simulation.server import serve_tts
from app.simulation.truck import Truck


async def simulation():
    """
    Simulates the cars that are moving through the routes
    """
    maps_client = MapsClient()
    pub_sub_client = PubSubClient.create(service_file="../var/pub-sub-sa.json")
    journeys = []

    route1 = Route.from_origin_and_destination(
        maps_client=maps_client,
        origin_address="Vilnius, Lithuania",
        destination_address="Klaipeda, Lithuania",
    )
    route2 = Route.from_origin_and_destination(
        maps_client=maps_client,
        origin_address="Klaipeda, Lithuania",
        destination_address="Panevezys, Lithuania",
    )
    route3 = Route.from_origin_and_destination(
        maps_client=maps_client,
        origin_address="Siauliai, Lithuania",
        destination_address="Vilnius, Lithuania",
    )
    route4 = Route.from_origin_and_destination(
        maps_client=maps_client,
        origin_address="Panevezys, Lithuania",
        destination_address="Kaunas, Lithuania",
    )

    for i in range(1):
        journeys.append(
            Journey.create(
                truck=Truck.create(location=LocationPoint(lat=0, lon=0)),
                route=route1,
                starting_delay=i * 10,
            )
        )

    for i in range(1):
        journeys.append(
            Journey.create(
                truck=Truck.create(location=LocationPoint(lat=0, lon=0)),
                route=route2,
                starting_delay=i * 7,
            )
        )

    journeys.append(
        Journey.create(
            truck=Truck.create(location=LocationPoint(lat=0, lon=0)),
            route=route3,
            starting_delay=0,
        )
    )

    journeys.append(
        Journey.create(
            truck=Truck.create(location=LocationPoint(lat=0, lon=0)),
            route=route4,
            starting_delay=0,
        )
    )

    await asyncio.gather(*[c.run() for c in journeys])

    await pub_sub_client.close()


async def populate_events(events_queue: asyncio.Queue[Event]):
    events = [
        (
            DeliveryRequestEvent.create(
                origin_address="Vilnius, Lithuania",
                destination_address="Klaipeda, Lithuania",
            ),
            5,
        ),
        (
            DeliveryRequestEvent.create(
                origin_address="Vilnius, Lithuania",
                destination_address="Klaipeda, Lithuania",
            ),
            5,
        ),
        (
            DeliveryRequestEvent.create(
                origin_address="Vilnius, Lithuania",
                destination_address="Klaipeda, Lithuania",
            ),
            5,
        ),
    ]

    for e, delay in events:
        await events_queue.put(e)
        await asyncio.sleep(delay)


async def tts_simulation(events_queue: asyncio.Queue[Event]):
    await asyncio.gather(
        serve_tts(events_queue),
        populate_events(events_queue),
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    queue: asyncio.Queue[Event] = asyncio.Queue()
    loop.run_until_complete(tts_simulation(queue))
