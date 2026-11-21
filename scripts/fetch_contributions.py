#!/usr/bin/env python3
"""Fetch accurate GitHub contribution activity into data/contributions.json.
Uses GitHub GraphQL (GITHUB_TOKEN/GH_TOKEN) so this remains within Actions auth.
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "contributions.json"
USER = os.getenv("GH_USERNAME", "RiteshRagav")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if not TOKEN:
    raise SystemExit("GH_TOKEN/GITHUB_TOKEN is required")

QUERY = r'''query($login:String!) {
  user(login:$login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}'''
r = requests.post("https://api.github.com/graphql", json={"query": QUERY, "variables": {"login": USER}},
                  headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}, timeout=30)
r.raise_for_status()
payload = r.json()
if payload.get("errors") or not payload.get("data", {}).get("user"):
    raise SystemExit(f"GitHub GraphQL error: {payload.get('errors') or 'user not found'}")
calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
days = [d for week in calendar["weeks"] for d in week["contributionDays"]]
# Month totals are grouped by YYYY-MM, then displayed as the most recent 12 months.
month_map = {}
for d in days:
    key = d["date"][:7]
    month_map[key] = month_map.get(key, 0) + int(d["contributionCount"])
months = [{"month": datetime.strptime(k, "%Y-%m").strftime("%b"), "key": k, "count": v}
          for k, v in sorted(month_map.items())][-12:]
counts = [int(d["contributionCount"]) for d in days]
active_days = sum(c > 0 for c in counts)
# Current streak is counted backwards from today only while every preceding
# calendar day is active. Longest streak scans the complete returned calendar.
by_date = {d["date"]: int(d["contributionCount"]) for d in days}
today = datetime.now(timezone.utc).date()
current = 0
cursor = today
while by_date.get(cursor.isoformat(), 0) > 0:
    current += 1
    from datetime import timedelta
    cursor -= timedelta(days=1)
longest = run = 0
for c in counts:
    run = run + 1 if c > 0 else 0
    longest = max(longest, run)
busiest = max(days, key=lambda d: int(d["contributionCount"]), default={"date":"—", "contributionCount":0})
out = {
  "username": USER,
  "updated_at": datetime.now(timezone.utc).isoformat(),
  "total_contributions": int(calendar["totalContributions"]),
  "current_streak": current,
  "longest_streak": longest,
  "active_days": active_days,
  "busiest_day": {"date": busiest.get("date", "—"), "count": int(busiest.get("contributionCount", 0))},
  "months": months,
  "days": [{"date": d["date"], "count": int(d["contributionCount"])} for d in days],
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"Updated contribution data for {USER}: {out['total_contributions']} contributions")
