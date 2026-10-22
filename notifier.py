from dotenv import load_dotenv
import os
import sys
import datetime
import requests
load_dotenv()

def log_error(message):
    print(f"{message}\n", file=sys.stderr)
    with open("./logs/error.log", "a") as file:
        file.write(f"{message}\n")

def message_warning(message):
    payload = {
        "chat_id": os.getenv("CHAT_ID"),
        "text": message
    }

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{os.getenv('BOT_KEY')}/sendMessage",
            json=payload,
            timeout=5
        )
    except requests.exceptions.RequestException as e:
        error_msg = f"[{timestamp}] ERROR - {e}"
        log_error(error_msg)
        return False
    else:
        if response.status_code != 200:
            error_data = response.json()
            error_msg = f"[{timestamp}] ERROR - {error_data['error_code']} = {error_data['description']}"
            log_error(error_msg)
            return False
        return True


if __name__ == "__main__":
    print("Sending test message to Telegram...")
    success = message_warning("\N{CHECK MARK} Test message from notifier.py — connection is working!")
    if success:
        print("Success! Check your Telegram.")
    else:
        print("Failed. Check error.log or stderr for details.")