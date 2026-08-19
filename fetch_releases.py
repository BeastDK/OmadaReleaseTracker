#!/usr/bin/env python3
"""
Henter Omada's offentlige release-kalender (Google Calendar), kategoriserer
events i Cloud / Private Cloud / On-Premises, gemmer resultatet i data.json,
og opdaterer changelog.json hvis der er sket ændringer (nye/fjernede events
eller flyttede datoer).

Bygger desuden docs/index.html (statisk side til GitHub Pages) ud fra
templates/index.html.jinja.

Miljøvariabler:
  CALENDAR_ICS_URL  - URL til kalenderens .ics-feed (public/basic.ics)
  LOOKBACK_DAYS     - hvor mange dage bagud der skal medtages (default 30)
  LOOKAHEAD_DAYS    - hvor mange dage frem der skal medtages (default 365)

Output (til brug i GitHub Actions):
  Skriver "changed=true"/"changed=false" til $GITHUB_OUTPUT hvis den findes,
  så workflowet kan afgøre om der skal sendes en mail.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, date, timezone
from pathlib import Path

import requests
import recurring_ical_events
from icalendar import Calendar
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
CHANGELOG_FILE = ROOT / "changelog.json"
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "templates"

DEFAULT_ICS_URL = (
    "https://calendar.google.com/calendar/ical/"
    "kinga.kostrzewa%40omadaidentity.com/public/basic.ics"
)

# Rækkefølgen betyder noget: mest specifikke mønster først.
CATEGORY_PATTERNS = [
    ("Private Cloud", re.compile(r"private\s*cloud", re.I)),
    ("On-Premises", re.compile(r"on[\s\-]?prem(ises)?", re.I)),
    ("Cloud", re.compile(r"\bcloud\b", re.I)),
]


def categorize(summary: str) -> str:
    for label, pattern in CATEGORY_PATTERNS:
        if pattern.search(summary or ""):
            return label
    return "Andet"


def to_iso_date(value) -> str:
    """Konverterer et icalendar dato/datetime-felt til 'YYYY-MM-DD'."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def fetch_events(ics_url: str, lookback_days: int, lookahead_days: int):
    resp = requests.get(ics_url, timeout=30)
    resp.raise_for_status()
    calendar = Calendar.from_ical(resp.content)

    start = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    end = datetime.now(timezone.utc) + timedelta(days=lookahead_days)

    # recurring_ical_events udfolder evt. tilbagevendende events i intervallet
    occurrences = recurring_ical_events.of(calendar).between(start, end)

    events = []
    for comp in occurrences:
        uid = str(comp.get("UID", ""))
        summary = str(comp.get("SUMMARY", "")).strip()
        description = str(comp.get("DESCRIPTION", "") or "").strip()
        dtstart = comp.get("DTSTART").dt if comp.get("DTSTART") else None
        iso_date = to_iso_date(dtstart) if dtstart is not None else None
        if not iso_date:
            continue

        events.append(
            {
                "uid": uid,
                "title": summary,
                "category": categorize(summary),
                "date": iso_date,
                "description": description,
            }
        )

    # Sorter og dedupliker (samme UID kan i sjældne tilfælde optræde 2x)
    seen = {}
    for ev in sorted(events, key=lambda e: (e["date"], e["title"])):
        key = ev["uid"] or f"{ev['title']}|{ev['date']}"
        seen[key] = ev
    return list(seen.values())


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def diff_events(old_events, new_events):
    """Finder tilføjede, fjernede og flyttede/omdøbte events."""

    def key(ev):
        return ev["uid"] or f"{ev['title']}|{ev['date']}"

    old_by_key = {key(e): e for e in old_events}
    new_by_key = {key(e): e for e in new_events}

    changes = []

    for k, new_ev in new_by_key.items():
        if k not in old_by_key:
            changes.append(
                {
                    "type": "added",
                    "category": new_ev["category"],
                    "title": new_ev["title"],
                    "date": new_ev["date"],
                }
            )
        else:
            old_ev = old_by_key[k]
            if old_ev["date"] != new_ev["date"]:
                changes.append(
                    {
                        "type": "moved",
                        "category": new_ev["category"],
                        "title": new_ev["title"],
                        "from": old_ev["date"],
                        "to": new_ev["date"],
                    }
                )
            elif old_ev["title"] != new_ev["title"]:
                changes.append(
                    {
                        "type": "renamed",
                        "category": new_ev["category"],
                        "from_title": old_ev["title"],
                        "to_title": new_ev["title"],
                        "date": new_ev["date"],
                    }
                )

    for k, old_ev in old_by_key.items():
        if k not in new_by_key:
            changes.append(
                {
                    "type": "removed",
                    "category": old_ev["category"],
                    "title": old_ev["title"],
                    "date": old_ev["date"],
                }
            )

    return changes


def render_site(events, changelog):
    grouped = {"Cloud": [], "Private Cloud": [], "On-Premises": [], "Andet": []}
    for ev in sorted(events, key=lambda e: e["date"]):
        grouped.setdefault(ev["category"], []).append(ev)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("index.html.jinja")
    html = template.render(
        grouped=grouped,
        changelog=list(reversed(changelog)),  # nyeste øverst
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")


def write_github_output(changed: bool):
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")


def main():
    ics_url = os.environ.get("CALENDAR_ICS_URL", DEFAULT_ICS_URL)
    lookback = int(os.environ.get("LOOKBACK_DAYS", "30"))
    lookahead = int(os.environ.get("LOOKAHEAD_DAYS", "365"))

    print(f"Henter kalender fra: {ics_url}")
    new_events = fetch_events(ics_url, lookback, lookahead)
    print(f"Fandt {len(new_events)} events i intervallet.")

    old_state = load_json(DATA_FILE, {"events": []})
    old_events = old_state.get("events", [])

    changes = diff_events(old_events, new_events)

    changelog = load_json(CHANGELOG_FILE, [])
    if changes:
        changelog.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "changes": changes,
            }
        )
        save_json(CHANGELOG_FILE, changelog)
        print(f"Registrerede {len(changes)} ændring(er):")
        for c in changes:
            print(f"  - {c}")
    else:
        print("Ingen ændringer fundet.")

    save_json(DATA_FILE, {"events": new_events, "updated_at": datetime.now(timezone.utc).isoformat()})
    render_site(new_events, changelog)
    write_github_output(bool(changes))

    # Skriv en simpel changes-summary til brug i mail-workflowet
    summary_path = ROOT / "last_changes.txt"
    if changes:
        lines = []
        for c in changes:
            if c["type"] == "moved":
                lines.append(f"[{c['category']}] '{c['title']}' flyttet: {c['from']} -> {c['to']}")
            elif c["type"] == "added":
                lines.append(f"[{c['category']}] Ny event: '{c['title']}' ({c['date']})")
            elif c["type"] == "removed":
                lines.append(f"[{c['category']}] Fjernet: '{c['title']}' ({c['date']})")
            elif c["type"] == "renamed":
                lines.append(f"[{c['category']}] Omdøbt: '{c['from_title']}' -> '{c['to_title']}' ({c['date']})")
        summary_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        summary_path.write_text("", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"FEJL: {exc}", file=sys.stderr)
        raise
