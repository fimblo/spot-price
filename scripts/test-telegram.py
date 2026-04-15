#!/usr/bin/env python3
"""Minimal Telegram test — sends a single message to verify credentials."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
from src.notify import send_message

load_dotenv()

token   = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

if not token or not chat_id:
    sys.exit("ERROR: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")

import requests

url = f"https://api.telegram.org/bot{token}/sendMessage"
print(f"Sending to chat_id={chat_id} ...")
resp = requests.post(url, data={'chat_id': chat_id, 'text': 'Hello from spot-price bot!'})
print(f"HTTP {resp.status_code}: {resp.text}")
