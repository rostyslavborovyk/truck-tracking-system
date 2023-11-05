import asyncio
import json
import logging

from telebot import TeleBot  # type: ignore[import-untyped]
from telebot.types import Message  # type: ignore[import-untyped]

from app.config import TELEGRAM_API_TOKEN
from app.telegram_bot_server.schemas import Notification

bot = TeleBot(TELEGRAM_API_TOKEN)

notifications_chat_ids = []

logger = logging.getLogger(__name__)


@bot.message_handler(commands=["info"])
def info(message: Message):
    if message.chat.id not in notifications_chat_ids:
        notifications_chat_ids.append(message.chat.id)
    data = f"""
    Bot sends important notification about Truck Tracking system
    
    Subscribed chat ids: {', '.join([str(i) for i in notifications_chat_ids])}
    
    Querying an info automatically subscribes you to the notifications
    """
    bot.send_message(message.chat.id, data)


def get_message(notification: Notification) -> str:
    return f"""
    New notification from Truck Tracking System

Event: {notification.event_type}

Additional info: {json.dumps(notification.additional_data)}
    """


async def send_telegram_messages(queue: asyncio.Queue[Notification]):
    while True:
        notification = await queue.get()
        logger.info(
            f"Got new notification, will send for chat ids {notifications_chat_ids}"
        )
        for chat_id in notifications_chat_ids:
            bot.send_message(chat_id, get_message(notification))


# start in separate thread
def serve_telegram_bot():
    logger.info("Starting polling for Telegram messages...")
    bot.polling()


if __name__ == "__main__":
    serve_telegram_bot()
