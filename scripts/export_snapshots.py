"""Copies AI results from the local cache into snapshots/, so they can be committed and reused after a deploy.

Run from the project folder:  PYTHONPATH=backend .venv/bin/python scripts/export_snapshots.py
"""
from finn.cache import SNAPSHOT_PREFIXES, _cache, snapshot_load, snapshot_save
from finn.pull.analysis import MIN_PROMISES_FOR_SCORE

saved = skipped = 0
for key in _cache.iterkeys():
    if not isinstance(key, str) or not key.startswith(SNAPSHOT_PREFIXES):
        continue
    value = _cache.get(key)
    # Thin analyses are left out so a later run can produce a better one
    if value is None or (key.startswith("analysis:") and len(value.get("promises", [])) < MIN_PROMISES_FOR_SCORE):
        skipped += 1
        continue
    if snapshot_load(key) is None:
        snapshot_save(key, value)
        saved += 1
        print("saved", key[:90])

print(f"\n{saved} new snapshots saved, {skipped} skipped")
