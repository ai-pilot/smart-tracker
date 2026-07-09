import html
import re
import time
import traceback

from . import diff as diffmod
from . import ai, telegram_api
from .config import DEFAULT_INTERVAL_MIN, TRACKER_TYPES
from .fetcher import fetch_page_text
from .shorten import shorten_url
from .store import get_tracker, load_state, new_tracker, save_state

URL_RE = re.compile(r"https?://\S+")

HELP = """<b>🤖 Smart Tracker Bot</b>

Send me a link + what you want tracked, e.g.:
<i>https://example.com/product  track the price</i>

The AI brain auto-picks the right tracker type.

<b>Commands</b>
/track &lt;url&gt; &lt;purpose&gt; — add a tracker
/list — show all trackers
/remove &lt;id&gt; — delete a tracker
/interval &lt;id&gt; &lt;minutes&gt; — change check interval
/heartbeat &lt;id&gt; on|off — also message when nothing changed
/removed &lt;id&gt; on|off — report items disappearing (default on)
/type &lt;id&gt; &lt;type&gt; — force a tracker type
/types — show the 10 tracker types
/now — check everything right now
/help — this message

⏱ Note: I run every 30 min, so replies to commands can take up to 30 min (or press Run workflow on GitHub for instant)."""


def notify(state, text):
    if state.get("chat_id"):
        telegram_api.send_message(state["chat_id"], text)


def handle_updates(state):
    force_run = False
    updates = telegram_api.get_updates(state["telegram_offset"])
    for u in updates:
        state["telegram_offset"] = u["update_id"] + 1
        msg = u.get("message") or {}
        text = (msg.get("text") or "").strip()
        chat_id = (msg.get("chat") or {}).get("id")
        if not text or not chat_id:
            continue
        if state["chat_id"] is None:
            state["chat_id"] = chat_id
        if chat_id != state["chat_id"]:
            continue
        try:
            if handle_command(state, text):
                force_run = True
        except Exception as e:
            notify(state, f"⚠️ Error handling '{html.escape(text[:50])}': {html.escape(str(e)[:300])}")
    return force_run


def handle_command(state, text):
    lower = text.lower()
    cmd = lower.split()[0] if lower.startswith("/") else ""
    if cmd in ("/start", "/help"):
        notify(state, HELP)
    elif cmd == "/types":
        lines = ["<b>Tracker types</b> (AI auto-picks; force with /type &lt;id&gt; &lt;key&gt;)"]
        lines += [f"• <code>{k}</code> — {v}" for k, v in TRACKER_TYPES.items()]
        notify(state, "\n".join(lines))
    elif cmd == "/list":
        if not state["trackers"]:
            notify(state, "No trackers yet. Send me a link!")
        else:
            lines = ["<b>Your trackers</b>"]
            for t in state["trackers"]:
                hb = " 💓" if t["heartbeat"] else ""
                rm = "" if t.get("report_removed", True) else " 🚫removed"
                lines.append(
                    f"#{t['id']} <b>{html.escape(t['name'] or '?')}</b> "
                    f"[{t['type']}] every {t['interval_min']}m{hb}{rm}\n{html.escape(t['url'])}"
                )
            notify(state, "\n\n".join(lines))
    elif cmd == "/remove":
        tid = _int_arg(text)
        t = get_tracker(state, tid)
        if t:
            state["trackers"].remove(t)
            notify(state, f"🗑 Removed #{tid} {html.escape(t['name'] or '')}")
        else:
            notify(state, f"Tracker #{tid} not found.")
    elif cmd == "/interval":
        parts = text.split()
        tid = _int_arg(text)
        t = get_tracker(state, tid)
        if t and len(parts) >= 3 and parts[2].isdigit():
            t["interval_min"] = max(30, int(parts[2]))
            notify(state, f"⏱ #{tid} now checks every {t['interval_min']} min (30 min minimum — that's how often I wake up).")
        else:
            notify(state, "Usage: /interval <id> <minutes>")
    elif cmd == "/heartbeat":
        parts = text.split()
        tid = _int_arg(text)
        t = get_tracker(state, tid)
        if t and len(parts) >= 3 and parts[2].lower() in ("on", "off"):
            t["heartbeat"] = parts[2].lower() == "on"
            notify(state, f"💓 Heartbeat for #{tid}: {parts[2].lower()}")
        else:
            notify(state, "Usage: /heartbeat <id> on|off")
    elif cmd == "/removed":
        parts = text.split()
        tid = _int_arg(text)
        t = get_tracker(state, tid)
        if t and len(parts) >= 3 and parts[2].lower() in ("on", "off"):
            t["report_removed"] = parts[2].lower() == "on"
            notify(state, f"🗑 Report removed items for #{tid}: {parts[2].lower()}")
        else:
            notify(state, "Usage: /removed <id> on|off")
    elif cmd == "/type":
        parts = text.split()
        tid = _int_arg(text)
        t = get_tracker(state, tid)
        if t and len(parts) >= 3 and parts[2] in TRACKER_TYPES:
            t["type"] = parts[2]
            t["snapshot"] = None
            notify(state, f"🔧 #{tid} type set to {parts[2]}. Re-baselining on next run.")
        else:
            notify(state, f"Usage: /type <id> <{'|'.join(TRACKER_TYPES)}>")
    elif cmd == "/now":
        for t in state["trackers"]:
            t["last_run"] = 0
        notify(state, "🏃 Checking all trackers now...")
        return True
    else:
        m = URL_RE.search(text)
        if m:
            url = m.group(0).rstrip(">,)")
            purpose = (text[: m.start()] + text[m.end():]).replace("/track", "").strip()
            create_tracker(state, url, purpose)
        elif not text.startswith("/"):
            notify(state, "Send me a link (optionally with what to track), or /help.")
        else:
            notify(state, "Unknown command. /help")
    return False


def _int_arg(text):
    parts = text.split()
    if len(parts) >= 2:
        p = parts[1].lstrip("#")
        if p.isdigit():
            return int(p)
    return -1


def create_tracker(state, url, purpose):
    notify(state, f"🧠 Analyzing {html.escape(url)} ...")
    page = fetch_page_text(url)
    plan = ai.classify(url, purpose, page)
    t = new_tracker(state, url, purpose)
    t["type"] = plan.get("type") if plan.get("type") in TRACKER_TYPES else "generic"
    t["name"] = plan.get("name") or url[:40]
    t["instructions"] = plan.get("instructions") or purpose or "track any change"
    t["interval_min"] = DEFAULT_INTERVAL_MIN
    t["report_removed"] = plan.get("report_removed", True)
    t["short_url"] = shorten_url(url)
    if plan.get("feasible") is False:
        notify(
            state,
            f"⚠️ #{t['id']}: {html.escape(plan.get('feasibility_note') or 'Page may be JS-only or blocked')} — I'll still try.",
        )
    snap = ai.extract(t, page)
    t["snapshot"] = snap
    t["last_run"] = int(time.time())
    notify(state, diffmod.format_full(t, snap))
    notify(
        state,
        f"ℹ️ Auto-selected type <code>{t['type']}</code>. Wrong? /type {t['id']} &lt;key&gt; — see /types",
    )


def run_tracker(state, t):
    if not t.get("short_url"):
        t["short_url"] = shorten_url(t["url"])
    try:
        page = fetch_page_text(t["url"])
        snap = ai.extract(t, page)
    except Exception as e:
        t["errors"] += 1
        if t["errors"] in (3, 10):
            notify(
                state,
                f"⚠️ #{t['id']} {html.escape(t['name'] or '')} failed {t['errors']} times in a row: {html.escape(str(e)[:200])}",
            )
        return
    t["errors"] = 0
    t["last_run"] = int(time.time())
    if t["snapshot"] is None:
        t["snapshot"] = snap
        notify(state, diffmod.format_full(t, snap))
        return
    added, removed, changed = diffmod.diff_snapshots(t["snapshot"], snap)
    if not snap.get("items") and t["snapshot"].get("items"):
        return
    reported_removed = removed if t.get("report_removed", True) else []
    if added or reported_removed or changed:
        notify(
            state,
            diffmod.format_changes(t, added, reported_removed, changed, snap.get("summary")),
        )
        t["snapshot"] = snap
    elif t["heartbeat"]:
        notify(
            state,
            f"💓 #{t['id']} {html.escape(t['name'] or '')}: no change ({len(snap.get('items', []))} items).",
        )


def run_due_trackers(state):
    now = time.time()
    for t in state["trackers"]:
        if now - t["last_run"] >= (t["interval_min"] or DEFAULT_INTERVAL_MIN) * 60 - 120:
            run_tracker(state, t)
            save_state(state)


def main():
    state = load_state()
    try:
        handle_updates(state)
    except Exception:
        traceback.print_exc()
    save_state(state)
    run_due_trackers(state)
    save_state(state)
    print(f"Done. {len(state['trackers'])} tracker(s).")


if __name__ == "__main__":
    main()
