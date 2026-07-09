import requests


def shorten_url(url):
    try:
        resp = requests.get(
            "https://tinyurl.com/api-create.php",
            params={"url": url},
            timeout=15,
        )
        if resp.status_code == 200 and resp.text.startswith("http"):
            return resp.text.strip()
    except Exception:
        pass
    return url
