import asyncio

from app.clients.maps import MapsClient
from app.clients.pub_sub import PubSubClient
from app.simulation.event import Event
from app.simulation.fleet import Fleet
from app.simulation.truck import Truck
from app.simulation.tts import TTS


async def serve_tts(events_queue: asyncio.Queue[Event]):
    maps_client = MapsClient()

    # service file for the service account will be already bind to the Cloud Run instance
    pub_sub_client = PubSubClient.create(service_file=None)

    trucks = [
        Truck.create(
            location=maps_client.get_location("Vilnius, Lithuania"),
            max_load_weight=5000,
        ),
        Truck.create(
            location=maps_client.get_location("Kaunas, Lithuania"),
            max_load_weight=10000,
        ),
        Truck.create(
            location=maps_client.get_location("Klaipeda, Lithuania"),
            max_load_weight=15000,
        ),
    ]

    fleet = Fleet(trucks=trucks)
    tts = TTS(
        maps_client=maps_client,
        pub_sub_client=pub_sub_client,
        events_queue=events_queue,
        fleet=fleet,
        journeys=[],
    )
    await tts.run()
