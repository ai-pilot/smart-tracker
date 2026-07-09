import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "state.json"


def _load_dotenv():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MAX_PAGE_CHARS = int(os.environ.get("MAX_PAGE_CHARS", "60000"))
DEFAULT_INTERVAL_MIN = int(os.environ.get("DEFAULT_INTERVAL_MIN", "30"))

TRACKER_TYPES = {
    "price": "💰 Price tracker",
    "catalog": "🆕 New/removed items tracker",
    "stock": "📦 Stock/restock tracker",
    "threshold": "🎯 Price threshold alert",
    "flight": "✈️ Flight/travel fare tracker",
    "jobs": "💼 Job listings tracker",
    "realestate": "🏠 Real-estate listings tracker",
    "news": "📰 News/keyword tracker",
    "rate": "📈 Currency/crypto/stock rate",
    "generic": "🔍 Generic change watcher",
}
