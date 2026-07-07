from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import MAX_PAGE_CHARS

MAX_PAGES = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _find_next_url(soup, current_url):
    link = soup.find("a", rel="next") or soup.find(
        "a", class_=lambda c: c and "next" in c.split()
    )
    if link and link.get("href"):
        nxt = urljoin(current_url, link["href"])
        if nxt != current_url:
            return nxt
    return None


def fetch_page_text(url):
    parts = []
    seen = set()
    current = url
    for page_no in range(1, MAX_PAGES + 1):
        if current in seen:
            break
        seen.add(current)
        resp = requests.get(current, headers=HEADERS, timeout=60, allow_redirects=True)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "json" in ctype:
            parts.append(resp.text)
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [ln for ln in text.splitlines() if ln.strip()]
        parts.append(f"[PAGE {page_no}: {current}]\n" + "\n".join(lines))
        if sum(len(p) for p in parts) >= MAX_PAGE_CHARS:
            break
        nxt = _find_next_url(soup, current)
        if not nxt:
            break
        current = nxt
    return "\n\n".join(parts)[:MAX_PAGE_CHARS]
