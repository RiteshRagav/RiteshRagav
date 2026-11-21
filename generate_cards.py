#!/usr/bin/env python3
"""Render animated, GitHub-README-safe SVG profile cards.

Input: data/contributions.json (refresh it from a scheduled workflow).
Run:   python generate_cards.py
       STATIC=1 python generate_cards.py   # animation disabled; final composition

The renderer deliberately uses only SVG + embedded CSS/SMIL. Optional fonts are
subset with pyftsubset when fontTools is installed and embedded as WOFF data URIs.
If no local font files are configured, the SVG uses a system-safe sans stack.
"""
from __future__ import annotations

import base64
import json
import math
import os
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import date, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cards"
DATA = ROOT / "data" / "contributions.json"
STATIC = os.getenv("STATIC", "0").strip().lower() in {"1", "true", "yes", "on"}

# Palette picked to echo the dark, minimal look of ritesh.tech. Change these
# tokens in one place to retheme every generated card.
BG = "#090B10"
PANEL = "#11151D"
PANEL_ALT = "#151B25"
BORDER = "#283140"
TEXT = "#F4F6FA"
MUTED = "#9AA7B8"
ACCENT = "#8B9CFF"
ACCENT_2 = "#63D6C5"
FONT_FAMILY = "RiteshSans, Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"

PROFILE = {
    "name": "Ritesh Ragav",
    "handle": "@RiteshRagav",
    "tagline": "Building reliable, scalable web applications.",
    "about": "Full-stack developer in the making · Backend-minded · AI systems enthusiast",
    "website": "https://www.ritesh.tech",
    "github": "https://github.com/RiteshRagav",
    "portrait": "",  # Optional absolute HTTPS image URL or data URI.
}

# Explicit project links from the portfolio. Replace a URL only if a different
# canonical repository is preferred; cards link directly to the project.
TILES = [
    {"title": "Portfolio", "subtitle": "Selected work & experiments", "url": PROFILE["website"], "symbol": "01"},
    {"title": "GitHub", "subtitle": "Code, projects & contributions", "url": PROFILE["github"], "symbol": "02"},
    {"title": "LinkedIn", "subtitle": "Professional profile", "url": "https://www.linkedin.com/in/riteshragav/", "symbol": "03"},
]

FEATURED = [
    {
        "name": "PaymentOrchestrator",
        "description": "Java project exploring payment orchestration and backend engineering.",
        "language": "Java",
        "url": "https://github.com/RiteshRagav/PaymentOrchestrator",
    },
    {
        "name": "CloudDoctor",
        "description": "AI-assisted cloud diagnostics project.",
        "language": "JavaScript",
        "url": "https://github.com/RiteshRagav/CloudDoctor",
    },
    {
        "name": "retail-location-bi",
        "description": "SaaS retail-location intelligence with multi-agent analysis.",
        "language": "Python",
        "url": "https://github.com/RiteshRagav/retail-location-bi",
    },
    {
        "name": "Observal",
        "description": "Observability and a local registry for MCPs, hooks, skills and graphRAGs.",
        "language": "Python",
        "url": "https://github.com/RiteshRagav/Observal",
    },
    {
        "name": "Mobility-Dreamer",
        "description": "An urban-mobility generative AI research project.",
        "language": "Python · Computer Vision",
        "url": "https://github.com/RiteshRagav/Mobility-Dreamer",
    },
]


def load_data() -> dict[str, Any]:
    if DATA.exists():
        try:
            data = json.loads(DATA.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: could not parse {DATA}: {exc}", file=sys.stderr)
    # Safe preview data. Workflow fetch replaces this with actual GitHub data.
    return {
        "username": "RiteshRagav",
        "updated_at": None,
        "total_contributions": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "active_days": 0,
        "busiest_day": {"date": "—", "count": 0},
        "months": [],
        "days": [],
    }


def subset_font() -> str:
    """Optionally subset assets/fonts/brand.ttf and return a WOFF data URI."""
    font_path = ROOT / "assets" / "fonts" / "brand.ttf"
    if not font_path.exists():
        return ""
    pyftsubset = shutil.which("pyftsubset")
    if not pyftsubset:
        print("pyftsubset not found; using system font fallback.", file=sys.stderr)
        return ""
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("repo-*.svg"):
        stale.unlink()
    woff = OUT / "brand-subset.woff"
    cmd = [pyftsubset, str(font_path), f"--output-file={woff}", "--flavor=woff",
           "--unicodes=U+0000-00FF", "--layout-features=*", "--name-IDs=*"]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    encoded = base64.b64encode(woff.read_bytes()).decode("ascii")
    return f"data:font/woff;base64,{encoded}"


def esc(value: Any) -> str:
    return escape(str(value if value is not None else ""), {'"': '&quot;'})


def wrap(text: str, width: int = 68) -> list[str]:
    return textwrap.wrap(str(text), width=width) or [""]


def svg_start(width: int, height: int, label: str, delay: float = 0.0,
              font_uri: str = "", radius: int = 24) -> str:
    font_css = (f"@font-face{{font-family:RiteshSans;src:url('{font_uri}') format('woff');font-display:swap}}"
                if font_uri else "")
    motion_css = "" if STATIC else f"""
      .card-enter {{ opacity:0; transform:translateY(22px); animation:enter .78s cubic-bezier(.2,.75,.2,1) {delay:.2f}s both; }}
      .draw {{ stroke-dasharray:1200; stroke-dashoffset:1200; animation:draw 1.2s ease-out {delay + .35:.2f}s forwards; }}
      .pulse {{ animation:pulse 3.6s ease-in-out {delay + .75:.2f}s infinite; transform-box:fill-box; transform-origin:center; }}
      @keyframes enter {{ to {{opacity:1; transform:translateY(0)}} }}
      @keyframes draw {{ to {{stroke-dashoffset:0}} }}
      @keyframes pulse {{ 0%,100% {{opacity:.62}} 50% {{opacity:1}} }}
      @media (prefers-reduced-motion: reduce) {{ *,*::before,*::after {{ animation:none!important; transition:none!important; }} .card-enter {{opacity:1;transform:none}} .draw {{stroke-dashoffset:0}} }}
    """
    if STATIC:
        motion_css = ".card-enter{opacity:1;transform:none}.draw{stroke-dashoffset:0}.pulse{opacity:1}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}">
  <title>{esc(label)}</title>
  <defs>
    <linearGradient id="surface" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{PANEL}"/><stop offset="1" stop-color="{PANEL_ALT}"/></linearGradient>
    <linearGradient id="glow" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{ACCENT}"/><stop offset="1" stop-color="{ACCENT_2}"/></linearGradient>
    <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="18"/></filter>
    <style>
      {font_css}
      text{{font-family:{FONT_FAMILY};fill:{TEXT}}} .muted{{fill:{MUTED}}} .accent{{fill:{ACCENT}}}
      .panel{{fill:url(#surface);stroke:{BORDER};stroke-width:1.2}} .small{{font-size:13px}} .label{{font-size:12px;letter-spacing:1.6px;font-weight:650}}
      {motion_css}
    </style>
  </defs>
  <rect x="1" y="1" width="{width-2}" height="{height-2}" rx="{radius}" class="panel"/>
  <g class="card-enter">
'''


def svg_end() -> str:
    return "  </g>\n</svg>\n"


def save(name: str, svg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("repo-*.svg"):
        stale.unlink()
    (OUT / name).write_text(svg, encoding="utf-8")
    print(f"Rendered {OUT / name}")


def hero(data: dict[str, Any], font_uri: str) -> None:
    w, h = 1000, 270
    s = svg_start(w, h, "Ritesh Ragav — profile introduction", 0.0, font_uri)
    s += f'''    <circle cx="860" cy="65" r="90" fill="{ACCENT}" opacity=".12" filter="url(#soft)"/>
    <path d="M0 220 C180 160 310 310 520 210 S810 110 1000 180" fill="none" stroke="url(#glow)" stroke-width="1.4" opacity=".28" class="draw"/>
    <text x="54" y="54" class="label accent">HELLO, I'M</text>
    <text x="54" y="118" font-size="48" font-weight="760" letter-spacing="-1.4">{esc(PROFILE['name'])}</text>
    <text x="56" y="158" font-size="20" font-weight="520">{esc(PROFILE['tagline'])}</text>
    <text x="56" y="194" font-size="14" class="muted">{esc(PROFILE['about'])}</text>
    <text x="56" y="237" font-size="13" class="muted">{esc(PROFILE['website'])}  ·  {esc(PROFILE['handle'])}</text>
'''
    portrait = PROFILE.get("portrait", "").strip()
    if portrait:
        s += f'''    <clipPath id="portraitClip"><circle cx="850" cy="132" r="76"/></clipPath>
    <image href="{esc(portrait)}" x="774" y="56" width="152" height="152" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>
    <circle cx="850" cy="132" r="78" fill="none" stroke="url(#glow)" stroke-width="2"/>
'''
    else:
        s += f'''    <circle cx="850" cy="132" r="76" fill="{PANEL_ALT}" stroke="url(#glow)" stroke-width="2"/>
    <text x="850" y="151" text-anchor="middle" font-size="58" font-weight="750" fill="{ACCENT}">RR</text>
'''
    s += svg_end()
    save("01-hero.svg", s)


def linked_tiles(font_uri: str) -> None:
    w, h = 1000, 190
    s = svg_start(w, h, "Three linked profile destinations", .6, font_uri)
    gap, tile_w = 18,  (w - 2 * 42 - 2 * 18) / 3
    for i, tile in enumerate(TILES):
        x = 42 + i * (tile_w + gap)
        s += f'''    <a href="{esc(tile['url'])}" xlink:href="{esc(tile['url'])}" target="_blank">
      <rect x="{x:.1f}" y="28" width="{tile_w:.1f}" height="132" rx="18" fill="{PANEL_ALT}" stroke="{BORDER}"/>
      <text x="{x+22:.1f}" y="61" class="label accent">{esc(tile['symbol'])}</text>
      <text x="{x+22:.1f}" y="98" font-size="22" font-weight="700">{esc(tile['title'])}</text>
      <text x="{x+22:.1f}" y="126" font-size="12" class="muted">{esc(tile['subtitle'])}</text>
      <path d="M{x+tile_w-42:.1f} 51 l10 0 l0 10 M{x+tile_w-52:.1f} 71 l20 -20" stroke="{ACCENT_2}" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </a>
'''
    s += svg_end()
    save("02-links.svg", s)


def contribution_chart(data: dict[str, Any], font_uri: str) -> None:
    months = data.get("months") or []
    months = months[-12:]
    total = int(data.get("total_contributions", 0) or 0)
    streak = int(data.get("current_streak", 0) or 0)
    active = int(data.get("active_days", 0) or 0)
    busiest = data.get("busiest_day") or {}
    busy_date = busiest.get("date", "—") if isinstance(busiest, dict) else "—"
    busy_count = int(busiest.get("count", 0) or 0) if isinstance(busiest, dict) else 0
    w, h = 1000, 340
    s = svg_start(w, h, "Monthly contributions and activity summary", 1.2, font_uri)
    s += '''    <text x="42" y="48" class="label accent">ACTIVITY OVERVIEW</text>
'''
    metrics = [("TOTAL CONTRIBUTIONS", str(total)), ("CURRENT STREAK", f"{streak} days"),
               ("ACTIVE DAYS", str(active)), ("BUSIEST DAY", f"{busy_date} · {busy_count}")]
    for i, (label, value) in enumerate(metrics):
        x = 42 + i * 235
        s += f'''    <text x="{x}" y="91" class="label muted">{esc(label)}</text>
    <text x="{x}" y="124" font-size="25" font-weight="720">{esc(value)}</text>
'''
    s += f'''    <path d="M42 152 H958" stroke="{BORDER}"/>
    <text x="42" y="186" font-size="14" font-weight="650">Contributions per month</text>
'''
    chart_x, chart_y, chart_w, chart_h = 60, 210, 880, 92
    maxv = max([int(m.get("count", 0)) for m in months if isinstance(m, dict)] + [1])
    if not months:
        s += f'''    <text x="{chart_x}" y="250" font-size="13" class="muted">Monthly contribution history will appear after the daily data refresh.</text>
'''
    else:
        n = len(months); slot = chart_w / n; bar_w = min(40, slot * .55)
        for i, m in enumerate(months):
            count = max(0, int(m.get("count", 0) or 0))
            label = str(m.get("month", ""))[:3]
            bh = (count / maxv) * chart_h
            x = chart_x + i * slot + (slot - bar_w) / 2
            y = chart_y + chart_h - bh
            s += f'''    <rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(2,bh):.1f}" rx="6" fill="url(#glow)" opacity=".9"/>
    <text x="{x+bar_w/2:.1f}" y="{chart_y+chart_h+22}" text-anchor="middle" class="small muted">{esc(label)}</text>
'''
    s += svg_end()
    save("03-activity.svg", s)


def repo_card(repo: dict[str, str], index: int, font_uri: str) -> None:
    w, h = 1000, 190
    delay = 1.9 + index * .55
    s = svg_start(w, h, f"Featured repository: {repo['name']}", delay, font_uri)
    s += f'''    <a href="{esc(repo['url'])}" xlink:href="{esc(repo['url'])}" target="_blank">
      <rect x="28" y="24" width="944" height="142" rx="18" fill="{PANEL_ALT}" stroke="{BORDER}"/>
      <rect x="28" y="24" width="4" height="142" rx="2" fill="url(#glow)"/>
      <text x="58" y="62" class="label accent">FEATURED REPOSITORY  /  {index:02d}</text>
      <text x="58" y="101" font-size="27" font-weight="720">{esc(repo['name'])}</text>
      <text x="58" y="128" font-size="14" class="muted">{esc(repo['description'])}</text>
      <text x="58" y="151" font-size="12" fill="{ACCENT_2}">{esc(repo['language'])}</text>
      <path d="M914 69 l18 0 l0 18 M906 87 l26 -18" stroke="{ACCENT_2}" stroke-width="2" fill="none" stroke-linecap="round"/>
    </a>
'''
    s += svg_end()
    save(f"repo-{index:02d}-{re.sub(r'[^a-z0-9]+','-',repo['name'].lower()).strip('-')}.svg", s)


def contribution_graph(data: dict[str, Any], font_uri: str) -> None:
    days = data.get("days") or []
    # Each day: {date: YYYY-MM-DD, count: integer}. Display up to 53 weeks.
    parsed = []
    for item in days[-371:]:
        try:
            d = date.fromisoformat(item["date"])
            parsed.append((d, max(0, int(item.get("count", 0)))))
        except (KeyError, TypeError, ValueError):
            continue
    w, h = 1000, 220
    s = svg_start(w, h, "GitHub contribution graph", 4.5, font_uri)
    s += f'''    <text x="42" y="45" class="label accent">CONTRIBUTION MAP</text>
    <text x="42" y="72" font-size="13" class="muted">Daily activity · brand-colour intensity</text>
'''
    x0, y0, cell, gap = 42, 98, 11, 4
    if parsed:
        max_count = max((c for _, c in parsed), default=1) or 1
        first = parsed[0][0]
        # Align first cell to the first Sunday in the visible calendar.
        offset = (first.weekday() + 1) % 7
        for i, (day, count) in enumerate(parsed):
            pos = i + offset
            col, row = pos // 7, pos % 7
            intensity = count / max_count
            fills = ["#202938", "#39465F", "#5869A1", ACCENT, ACCENT_2]
            level = 0 if count == 0 else min(4, 1 + int(intensity * 3.99))
            x, y = x0 + col * (cell + gap), y0 + row * (cell + gap)
            s += f'''    <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fills[level]}" opacity=".95"><title>{day.isoformat()}: {count} contributions</title></rect>
'''
    else:
        s += f'''    <text x="42" y="135" font-size="13" class="muted">The contribution grid will populate when data/contributions.json is refreshed.</text>
'''
    s += svg_end()
    save("99-contribution-graph.svg", s)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("repo-*.svg"):
        stale.unlink()
    data = load_data()
    font_uri = subset_font()
    hero(data, font_uri)
    linked_tiles(font_uri)
    contribution_chart(data, font_uri)
    for i, repo in enumerate(FEATURED, 1):
        repo_card(repo, i, font_uri)
    contribution_graph(data, font_uri)
    print(f"Done: generated SVG cards in {OUT} (STATIC={int(STATIC)})")


if __name__ == "__main__":
    main()
