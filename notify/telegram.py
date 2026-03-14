"""Send a Telegram message via Bot API."""
import json
import urllib.request

from loguru import logger


def send_message(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                logger.info("Telegram message sent.")
                return True
            logger.error(f"Telegram API error: {result}")
            return False
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False
