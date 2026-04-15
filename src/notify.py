import os
import requests

_API = 'https://api.telegram.org/bot{token}/{method}'


def send_message(token: str, chat_id: str, text: str) -> bool:
    """
    Send a text message via the Telegram Bot API.

    Returns True on success, False on any error.
    """
    url = _API.format(token=token, method='sendMessage')
    try:
        response = requests.post(url, data={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
        })
        return response.ok
    except Exception:
        return False


def send_photo(token: str, chat_id: str, photo_path: str, caption: str = '') -> bool:
    """
    Send a photo (PNG/JPG file) with an optional HTML caption via Telegram.

    Returns True on success, False when the file is missing or on any error.
    """
    if not os.path.exists(photo_path):
        return False

    url = _API.format(token=token, method='sendPhoto')
    try:
        with open(photo_path, 'rb') as fh:
            response = requests.post(url,
                data={
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML',
                },
                files={'photo': fh},
            )
        return response.ok
    except Exception:
        return False
