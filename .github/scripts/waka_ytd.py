#!/usr/bin/env python3
"""Build a year-to-date (01 Jan -> today) WakaTime stats block and inject it
into README.md between the <!--START_SECTION:waka--> markers.

The stock athul/waka-readme action only supports preset ranges (last_7_days,
last_year, ...). This script hits the WakaTime `summaries` endpoint with an
explicit start/end so the range is the current calendar year to date.
"""
import os
import sys
import re
import json
import base64
import datetime
import urllib.request

KEY = os.environ["WAKATIME_API_KEY"]
BLOCKS = "⣀⣄⣤⣦⣶⣷⣿"   # 7 fill levels, matches the existing block style
BAR = 25                # progress-bar width in cells
TOP_N = 6               # languages to list

today = datetime.date.today()
start = datetime.date(today.year, 1, 1)

url = (
    "https://wakatime.com/api/v1/users/current/summaries"
    f"?start={start.isoformat()}&end={today.isoformat()}"
)
auth = base64.b64encode(KEY.encode()).decode()
req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
with urllib.request.urlopen(req, timeout=90) as resp:
    payload = json.load(resp)

# Aggregate seconds per language across every day in the range.
agg = {}
for day in payload.get("data", []):
    for lang in day.get("languages", []):
        agg[lang["name"]] = agg.get(lang["name"], 0) + lang.get("total_seconds", 0)

total = sum(agg.values())
if total <= 0:
    print("No coding activity in range; leaving README unchanged.")
    sys.exit(0)


def bar_for(pct):
    exact = pct / 100 * BAR
    full = int(exact)
    idx = round((exact - full) * 6)   # which partial cell (0..6)
    partial = ""
    if idx == 6:
        full += 1
    elif idx > 0:
        partial = BLOCKS[idx]
    empty = BAR - full - (1 if partial else 0)
    return "⣿" * full + partial + "⣀" * max(empty, 0)


def fmt_time(secs):
    secs = int(secs)
    return f"{secs // 3600} hrs {(secs % 3600) // 60} mins"


rows = []
for name, secs in sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]:
    pct = secs / total * 100
    rows.append(f"{name:<18} {fmt_time(secs):<20} {bar_for(pct)}   {pct:05.2f} %")

th, tm = int(total) // 3600, (int(total) % 3600) // 60
block = (
    "```txt\n"
    f"From: {start.strftime('%d %B %Y')} - To: {today.strftime('%d %B %Y')}\n\n"
    f"Total Time: {th:,} hrs {tm} mins\n\n"
    + "\n".join(rows)
    + "\n```"
)

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

new = re.sub(
    r"(<!--START_SECTION:waka-->)[\s\S]*?(<!--END_SECTION:waka-->)",
    lambda m: f"{m.group(1)}\n\n{block}\n\n{m.group(2)}",
    readme,
)

if new == readme:
    print("Markers not found or content already current; no write.")
else:
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new)
    print("README updated with year-to-date WakaTime stats.")
