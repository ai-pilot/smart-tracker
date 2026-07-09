import html

MAX_NAME_LEN = 60
MAX_LIST_ITEMS = 25


def _esc(s):
    return html.escape(str(s or ""))


def _trim(s, n=MAX_NAME_LEN):
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def diff_snapshots(old, new):
    old_items = {i["key"]: i for i in old.get("items", [])}
    new_items = {i["key"]: i for i in new.get("items", [])}
    added = [i for k, i in new_items.items() if k not in old_items]
    removed = [i for k, i in old_items.items() if k not in new_items]
    changed = [
        (old_items[k], i)
        for k, i in new_items.items()
        if k in old_items and str(old_items[k].get("value")) != str(i.get("value"))
    ]
    return added, removed, changed


def _item_line(i):
    line = f"• <b>{_esc(_trim(i.get('key')))}</b>"
    if i.get("value"):
        line += f" — {_esc(i['value'])}"
    if i.get("detail"):
        line += f"\n   <i>{_esc(_trim(i['detail'], 80))}</i>"
    return line


def _capped(items, limit=MAX_LIST_ITEMS):
    if len(items) <= limit:
        return "\n".join(_item_line(i) for i in items), 0
    shown = items[:limit]
    return "\n".join(_item_line(i) for i in shown), len(items) - limit


def _tracker_url(tracker):
    return tracker.get("short_url") or tracker.get("url")


def format_full(tracker, snap):
    items = snap.get("items", [])
    lines = [
        f"🆕 <b>#{tracker['id']} {_esc(tracker['name'])}</b> — tracker created",
        f"Type: <code>{tracker['type']}</code> · every {tracker['interval_min']} min",
    ]
    if snap.get("summary"):
        lines.append(_esc(snap["summary"]))
    lines.append("")

    by_cat = {}
    for i in items:
        by_cat.setdefault(i.get("category") or "", []).append(i)

    for cat in sorted(by_cat, key=lambda c: (c == "", c)):
        cat_items = by_cat[cat]
        if cat:
            lines.append(f"<b>📂 {_esc(cat)}</b> ({len(cat_items)})")
        body, extra = _capped(cat_items)
        lines.append(body)
        if extra:
            lines.append(f"<i>…and {extra} more</i>")
        lines.append("")

    lines.append("I'll message you only when something changes.")
    lines.append(f"🔗 {_esc(_tracker_url(tracker))}")
    return "\n".join(lines).strip()


def format_changes(tracker, added, removed, changed, summary):
    lines = [f"🔔 <b>#{tracker['id']} {_esc(tracker['name'])}</b> — change detected"]

    if added:
        lines.append(f"\n➕ <b>New</b> ({len(added)})")
        body, extra = _capped(added)
        lines.append(body)
        if extra:
            lines.append(f"<i>…and {extra} more</i>")

    if changed:
        lines.append(f"\n🔁 <b>Price/value changed</b> ({len(changed)})")
        shown = changed[:MAX_LIST_ITEMS]
        for old, new in shown:
            lines.append(
                f"• <b>{_esc(_trim(new.get('key')))}</b>\n"
                f"   {_esc(old.get('value'))} → <b>{_esc(new.get('value'))}</b>"
            )
        if len(changed) > MAX_LIST_ITEMS:
            lines.append(f"<i>…and {len(changed) - MAX_LIST_ITEMS} more</i>")

    if removed:
        lines.append(f"\n➖ <b>Removed</b> ({len(removed)})")
        body, extra = _capped(removed)
        lines.append(body)
        if extra:
            lines.append(f"<i>…and {extra} more</i>")

    if summary:
        lines.append(f"\n<i>{_esc(summary)}</i>")
    lines.append(f"🔗 {_esc(_tracker_url(tracker))}")
    return "\n".join(lines).strip()
