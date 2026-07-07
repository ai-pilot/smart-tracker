import requests

from .config import TELEGRAM_BOT_TOKEN

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def get_updates(offset):
    resp = requests.get(
        f"{API}/getUpdates",
        params={"offset": offset, "timeout": 0, "allowed_updates": '["message"]'},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


def send_message(chat_id, text):
    for chunk in _split(text):
        resp = requests.post(
            f"{API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            requests.post(
                f"{API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )


def _split(text, limit=3900):
    if len(text) <= limit:
        return [text]
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks
