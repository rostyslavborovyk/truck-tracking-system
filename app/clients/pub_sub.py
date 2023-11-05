import asyncio
import json

from gcloud.aio.pubsub import PublisherClient, PubsubMessage
from pydantic import BaseModel

from app.simulation.log import Log

PROJECT_ID = "cloud-computing-project-403820"
SERVICE_ACCOUNT_FILENAME = "simulation-sa.json"

IOT_EVENTS_TOPIC_NAME = "iot-events"
FULL_IOT_EVENTS_TOPIC_NAME = f"projects/{PROJECT_ID}/topics/{IOT_EVENTS_TOPIC_NAME}"

DOMAIN_LOGS_TOPIC_NAME = "domain-logs"
FULL_DOMAIN_LOGS_TOPIC_NAME = f"projects/{PROJECT_ID}/topics/{DOMAIN_LOGS_TOPIC_NAME}"

JOURNEYS_TOPIC_NAME = "journeys"
FULL_JOURNEYS_TOPIC_NAME = f"projects/{PROJECT_ID}/topics/{JOURNEYS_TOPIC_NAME}"


class JourneyTrackEvent(BaseModel):
    truck_id: int
    lat: float
    lon: float
    timestamp: int
    color: str


class PubSubClient:
    def __init__(self, publisher_client: PublisherClient):
        self.publisher_client = publisher_client
        self._domain_logs_queue: asyncio.Queue[Log] = asyncio.Queue()

    @classmethod
    def create(cls, service_file: str | None = f"../var/{SERVICE_ACCOUNT_FILENAME}"):
        if service_file:
            publisher_client = PublisherClient(service_file=service_file)
        else:
            publisher_client = PublisherClient()
        return cls(publisher_client=publisher_client)

    async def publish_events(self, events: list[JourneyTrackEvent]):
        messages = [PubsubMessage(json.dumps(e.model_dump())) for e in events]
        await self.publisher_client.publish(FULL_IOT_EVENTS_TOPIC_NAME, messages)

    async def publish_domain_logs(self, logs: list[Log]):
        messages = []
        for log in logs:
            log_data = log.model_dump()
            log_data["data"] = json.dumps(log_data["data"])
            messages.append(PubsubMessage(json.dumps(log_data), type=log_data["type"]))

        await self.publisher_client.publish(FULL_DOMAIN_LOGS_TOPIC_NAME, messages)

    async def publish_journey(
        self, journey_id: int, truck_id: int, route_geography: str
    ) -> None:
        await self.publisher_client.publish(
            FULL_JOURNEYS_TOPIC_NAME,
            [
                PubsubMessage(
                    json.dumps(
                        {
                            "journey_id": journey_id,
                            "truck_id": truck_id,
                            "route_geography": route_geography,
                        }
                    )
                )
            ],
        )

    async def add_domain_log(self, log: Log):
        await self._domain_logs_queue.put(log)

    async def flush_domain_logs(self):
        while True:
            logs = []
            while not self._domain_logs_queue.empty():
                logs.append(await self._domain_logs_queue.get())

            if logs:
                await self.publish_domain_logs(logs)

            await asyncio.sleep(3)

    async def close(self):
        await self.publisher_client.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        PubSubClient.create().publish_events(
            [JourneyTrackEvent(truck_id=0, lat=0, lon=0, timestamp=1, color="#FF0000")]
        )
    )
