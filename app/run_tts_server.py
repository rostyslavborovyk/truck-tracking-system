import asyncio
import logging
from functools import partial

import uvicorn
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.simulation.event import DeliveryRequestEvent, Event
from app.simulation.server import serve_tts

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


class PostTriggerEventDeliveryRequest(BaseModel):
    load_weight: int
    origin_address: str
    destination_address: str

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        json_schema_extra={
            "examples": [
                {
                    "loadWeight": 1000,
                    "originAddress": "Vilnius, Lithuania",
                    "destinationAddress": "Siauliai, Lithuania",
                }
            ]
        },
    )


async def application_setup_signal(app_instance: FastAPI):
    events_queue: asyncio.Queue[Event] = asyncio.Queue()
    app_instance.state.events_queue = events_queue
    asyncio.create_task(serve_tts(events_queue))
    logger.info("Application was set up!")


async def application_shutdown_signal(app_instance: FastAPI):
    pass


app = FastAPI()


app.add_event_handler(
    "startup",
    partial(application_setup_signal, app_instance=app),
)
app.add_event_handler(
    "shutdown",
    partial(application_shutdown_signal, app_instance=app),
)


def get_events_queue(request: Request) -> asyncio.Queue[Event]:
    return request.app.state.events_queue


@app.post("/trigger-event/delivery-request")
async def delivery_request(
    payload: PostTriggerEventDeliveryRequest,
    events_queue: asyncio.Queue[Event] = Depends(get_events_queue),
) -> str:
    await events_queue.put(
        DeliveryRequestEvent.create(**payload.model_dump(by_alias=False))
    )
    return "Success"


if __name__ == "__main__":
    uvicorn.run(app)
