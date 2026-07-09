import json
import time

from .config import STATE_FILE

DEFAULT_STATE = {
    "telegram_offset": 0,
    "chat_id": None,
    "next_id": 1,
    "trackers": [],
    "pending": None,
}


TRACKER_FIELD_DEFAULTS = {
    "short_url": None,
    "heartbeat": False,
    "report_removed": True,
    "errors": 0,
}


def load_state():
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        for k, v in DEFAULT_STATE.items():
            state.setdefault(k, v)
        for t in state.get("trackers", []):
            for k, v in TRACKER_FIELD_DEFAULTS.items():
                t.setdefault(k, v)
        return state
    return dict(DEFAULT_STATE)


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def new_tracker(state, url, purpose):
    t = {
        "id": state["next_id"],
        "url": url,
        "short_url": None,
        "purpose": purpose,
        "type": None,
        "name": None,
        "instructions": None,
        "interval_min": None,
        "heartbeat": False,
        "report_removed": True,
        "last_run": 0,
        "snapshot": None,
        "created": int(time.time()),
        "errors": 0,
    }
    state["next_id"] += 1
    state["trackers"].append(t)
    return t


def get_tracker(state, tid):
    for t in state["trackers"]:
        if t["id"] == tid:
            return t
    return None
