import asyncio
import base64
import json
import logging
from functools import partial
from threading import Thread

import uvicorn
from fastapi import Depends, FastAPI, Request

from app.telegram_bot_server.schemas import Notification
from app.telegram_bot_server.server import send_telegram_messages, serve_telegram_bot

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
    level=logging.INFO,
)


app = FastAPI()


async def application_setup_signal(app_instance: FastAPI):
    events_queue: asyncio.Queue[Notification] = asyncio.Queue()
    app_instance.state.events_queue = events_queue
    asyncio.create_task(send_telegram_messages(events_queue))
    telegram_bot_thread = Thread(target=serve_telegram_bot)
    telegram_bot_thread.start()


app.add_event_handler(
    "startup",
    partial(application_setup_signal, app_instance=app),
)


def get_events_queue(request: Request) -> asyncio.Queue[Notification]:
    return request.app.state.events_queue


@app.post("/notifications")
async def notifications(
    request: Request,
    events_queue: asyncio.Queue[Notification] = Depends(get_events_queue),
) -> str:
    data = json.loads(await request.body())
    await events_queue.put(
        Notification(
            event_type=data["message"]["attributes"]["type"],
            additional_data=json.loads(
                base64.b64decode(data["message"]["data"]).decode("utf-8")
            ),
        )
    )
    return "Success"


if __name__ == "__main__":
    uvicorn.run(app, port=8001)
