import html


def _esc(s):
    return html.escape(str(s or ""))


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
    line = f"• <b>{_esc(i.get('key'))}</b>"
    if i.get("value"):
        line += f" — {_esc(i['value'])}"
    if i.get("detail"):
        line += f"\n   <i>{_esc(i['detail'])}</i>"
    return line


def format_full(tracker, snap):
    items = snap.get("items", [])
    lines = [
        f"🆕 <b>Tracker #{tracker['id']} created: {_esc(tracker['name'])}</b>",
        f"Type: {tracker['type']} | every {tracker['interval_min']} min",
        f"{_esc(snap.get('summary', ''))}",
        "",
    ]
    by_cat = {}
    for i in items:
        by_cat.setdefault(i.get("category") or "", []).append(i)
    for cat in sorted(by_cat):
        if cat:
            lines.append(f"\n<b>📂 {_esc(cat)} ({len(by_cat[cat])})</b>")
        lines.extend(_item_line(i) for i in by_cat[cat])
    lines.append("\nI will alert you only when something changes.")
    return "\n".join(lines)


def format_changes(tracker, added, removed, changed, summary):
    lines = [f"🔔 <b>Change in #{tracker['id']} {_esc(tracker['name'])}</b>"]
    if added:
        lines.append(f"\n➕ <b>New ({len(added)}):</b>")
        lines.extend(_item_line(i) for i in added)
    if removed:
        lines.append(f"\n➖ <b>Removed ({len(removed)}):</b>")
        lines.extend(_item_line(i) for i in removed)
    if changed:
        lines.append(f"\n🔁 <b>Changed ({len(changed)}):</b>")
        for old, new in changed:
            lines.append(
                f"• <b>{_esc(new.get('key'))}</b>: "
                f"{_esc(old.get('value'))} → <b>{_esc(new.get('value'))}</b>"
            )
    if summary:
        lines.append(f"\n{_esc(summary)}")
    lines.append(f"\n{_esc(tracker['url'])}")
    return "\n".join(lines)
