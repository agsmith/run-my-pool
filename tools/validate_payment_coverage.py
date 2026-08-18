"""Fail when a manual payment-matrix ID disappears from coverage documentation."""

from pathlib import Path
import re


SECTIONS = {"A": 4, "B": 5, "C": 6, "D": 7, "E": 10, "F": 5, "G": 6, "H": 6, "I": 6, "J": 4}
ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "docs/payment-entitlement-coverage.md").read_text()


def documented_ids(text):
    found = set(re.findall(r"\b[A-J]\d{2}\b", text))
    for section, start, end_section, end in re.findall(r"\b([A-J])(\d{2})-([A-J]?)(\d{2})\b", text):
        if end_section and end_section != section:
            continue
        for number in range(int(start), int(end) + 1):
            found.add(f"{section}{number:02d}")
    return found


required = {f"{section}{number:02d}" for section, count in SECTIONS.items() for number in range(1, count + 1)}
missing = sorted(required - documented_ids(TEXT))
if missing:
    raise SystemExit(f"Payment matrix IDs missing from coverage documentation: {', '.join(missing)}")
print(f"Payment coverage documentation accounts for all {len(required)} matrix cases.")
