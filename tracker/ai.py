import json
import re

import requests

from .config import (
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    TRACKER_TYPES,
)

_URL = (
    f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}"
    f"/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
)


def _call(prompt):
    body = {
        "messages": [
            {
                "role": "system",
                "content": "You are a precise data-extraction assistant. Always reply with valid JSON only, no prose, no markdown fences.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        _URL,
        headers={"Content-Type": "application/json", "api-key": AZURE_OPENAI_KEY},
        json=body,
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Azure OpenAI call failed: {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _parse_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


def classify(url, purpose, page_text):
    types_desc = "\n".join(f"- {k}: {v}" for k, v in TRACKER_TYPES.items())
    prompt = f"""You are the brain of a website change tracker bot.

The user wants to track this URL: {url}
User's stated purpose: {purpose or "(none given, infer it)"}

Available tracker types:
{types_desc}

Here is the text content of the page:
---
{page_text}
---

Decide how to track this page. Reply with JSON only:
{{
  "type": "<one of: {", ".join(TRACKER_TYPES)}>",
  "name": "<short human name for this tracker, max 6 words>",
  "instructions": "<precise instructions for a future extraction step: exactly what data to extract from this page each run so changes can be detected (e.g. 'extract every product with name, price, category; categorize Apple items into MacBook/iPhone/iPad/Watch/Accessories')>",
  "feasible": true/false,
  "feasibility_note": "<if page looks empty/blocked/js-only, say so, else ''>",
  "report_removed": true/false
}}
Set "report_removed" to false if the user's purpose implies they only care about new items appearing and/or price changes (e.g. "show only new additions and price changes"), not items disappearing. Default true otherwise."""
    return _parse_json(_call(prompt))


def extract(tracker, page_text):
    prompt = f"""You are extracting structured data for a change tracker.

Tracker type: {tracker["type"]}
Tracker name: {tracker["name"]}
User purpose: {tracker["purpose"]}
Extraction instructions: {tracker["instructions"]}

Page text:
---
{page_text}
---

Extract the data per the instructions. Reply with JSON only, in this shape:
{{
  "items": [
    {{"key": "<stable unique identifier, e.g. product name or flight+date>",
      "value": "<the tracked value, e.g. price '2,199 AED' or 'in stock'>",
      "category": "<category if relevant, else ''>",
      "detail": "<one-line extra detail, else ''>"}}
  ],
  "summary": "<one-line summary of what was found, with counts>"
}}
Rules:
- keys must be stable across runs (do not include timestamps or ranks).
- values should be normalized (keep currency symbols/units).
- If the page has a single tracked value (one price/rate), return one item.
- If nothing relevant found, return empty items and explain in summary."""
    return _parse_json(_call(prompt))
