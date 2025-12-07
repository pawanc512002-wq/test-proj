# storage.py
# Simple JSON file storage helpers. Thread-safe enough for a dev POC.

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "rfps": DATA_DIR / "rfps.json",
    "vendors": DATA_DIR / "vendors.json",
    "proposals": DATA_DIR / "proposals.json",
    "outbox": DATA_DIR / "outbox.json",
}

for f in FILES.values():
    if not f.exists():
        f.write_text("[]")


def read_json(key: str):
    p = FILES[key]
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def write_json(key: str, obj: Any):
    p = FILES[key]
    p.write_text(json.dumps(obj, indent=2, default=str))
