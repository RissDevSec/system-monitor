import os

import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def message_warning(message):
    payload = {
        "chat_id": os.getenv("CHAT_ID"),
        "text": message,
    }

    logger.debug("Sending Telegram notification ({} characters)", len(message))

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{os.getenv('BOT_KEY')}/sendMessage",
            json=payload,
            timeout=5,
        )
    except requests.exceptions.RequestException as e:
        logger.error("Failed to send Telegram notification: {}", e)
        return False
    else:
        if response.status_code != 200:
            error_data = response.json()
            logger.error(
                "Telegram API error [{}]: {}",
                error_data["error_code"],
                error_data["description"],
            )
            return False
        return True


if __name__ == "__main__":
    from logger_config import setup_logger

    setup_logger()

    logger.info("Sending test message to Telegram...")
    success = message_warning("\N{WHITE HEAVY CHECK MARK} Test message from notifier.py — connection is working!")
    if success:
        logger.success("Success! Check your Telegram.")
    else:
        logger.error("Failed. Check the logs for details.")
