"""
Utility to clear persisted `chat_history` entries from data/cache/ai_prompt_cache.json.
Run:
    python scripts\clear_persisted_history.py            # clears all chat_history lists
    python scripts\clear_persisted_history.py demo-provenance  # clear only that dataset key
"""
import json
import sys
from pathlib import Path

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "ai_prompt_cache.json"

if not CACHE.exists():
    import logging
    logging.getLogger(__name__).info("Cache file not found: %s", CACHE)
    sys.exit(1)

key_to_clear = sys.argv[1] if len(sys.argv) > 1 else None

with open(CACHE, "r", encoding="utf-8") as fh:
    payload = json.load(fh)

if not isinstance(payload, dict):
    import logging
    logging.getLogger(__name__).warning("Unexpected cache format")
    sys.exit(1)

modified = False
if key_to_clear:
    entry = payload.get(key_to_clear)
    if isinstance(entry, dict) and entry.get("chat_history"):
        entry["chat_history"] = []
        payload[key_to_clear] = entry
        modified = True
        import logging
        logging.getLogger(__name__).info("Cleared chat_history for dataset key: %s", key_to_clear)
    else:
        import logging
        logging.getLogger(__name__).info("No chat_history found for key: %s", key_to_clear)
else:
    for k, v in payload.items():
        if isinstance(v, dict) and v.get("chat_history"):
            v["chat_history"] = []
            payload[k] = v
            modified = True
    if modified:
        import logging
        logging.getLogger(__name__).info("Cleared chat_history for all dataset keys that had entries.")
    else:
        import logging
        logging.getLogger(__name__).info("No chat_history entries found to clear.")

if modified:
    temp = CACHE.with_suffix(".tmp")
    with open(temp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    temp.replace(CACHE)
    import logging
    logging.getLogger(__name__).info("Cache updated.")
else:
    import logging
    logging.getLogger(__name__).info("No changes made.")
