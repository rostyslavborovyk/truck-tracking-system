import asyncio
import random

import httpx

TTS_SERVER_BASE_URL = "https://tts-server-hjnfdwswgq-lm.a.run.app"
SEND_DELIVERY_REQUEST_URL = f"{TTS_SERVER_BASE_URL}/trigger-event/delivery-request"

CITIES = [
    "Siauliai, Lithuania",
    "Vilnius, Lithuania",
    "Klaipeda, Lithuania",
    "Kaunas, Lithuania",
    "Panevezys, Lithuania",
]


async def send_delivery_request(
    origin_address: str, destination_address: str, load_weight: int
) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            SEND_DELIVERY_REQUEST_URL,
            json={
                "destinationAddress": destination_address,
                "loadWeight": load_weight,
                "originAddress": origin_address,
            },
        )


async def main():
    while True:
        destination_address, origin_address = random.sample(CITIES, k=2)
        load_weight = int(random.random() * 20_000)
        print(
            f"Sent delivery request from {destination_address} to {origin_address} with weight {load_weight}"
        )
        await send_delivery_request(origin_address, destination_address, load_weight)
        await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
