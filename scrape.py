#!/usr/bin/env python3
"""WagerTalk free-picks scraper — Drew Martin & Jimmy Adams by default.

Fetches the WagerTalk free-sports-picks page with Playwright, parses the
rendered page text into structured picks, renders a static HTML page to
``docs/index.html`` and (unless told otherwise) commits and pushes it so
GitHub Pages stays fresh.

Command line::

    python3 scrape.py                     # fetch, write docs/index.html, git push
    python3 scrape.py --dry-run           # print the HTML, touch nothing
    python3 scrape.py --json              # print parsed picks as JSON, touch nothing
    python3 scrape.py --no-push           # write docs/index.html, skip git push
    python3 scrape.py --experts "A,B"     # track other cappers
    python3 scrape.py --url URL --out PATH

All parsing helpers are pure-text functions with no browser dependency, so the
whole pipeline except the network fetch is unit-testable offline.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

URL = "https://www.wagertalk.com/free-sports-picks"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(REPO_DIR, "docs", "index.html")
DEFAULT_EXPERTS = ("Drew Martin", "Jimmy Adams")

PROMO_RE = re.compile(r"released/revised|other\s+picks?\s*/\s*packages", re.IGNORECASE)


def fetch_text(url: str = URL) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Run: pip install playwright && python3 -m playwright install chromium")
        sys.exit(1)

    print("Launching browser...", file=sys.stderr)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Wait until picks are actually rendered (the capper list in the footer
        # is always present, so this is a reliable "page is done" marker).
        page.wait_for_selector("text=JIMMY ADAMS", timeout=20000)
        text = page.inner_text("body")
        browser.close()
    return text


def extract_field(block: str, label: str) -> str:
    """Return the value of ``label:`` in *block*, or ``""``.

    WagerTalk renders each label and its value as separate lines, usually with
    a blank line in between::

        Event:

        (909) Arizona Diamondbacks at (910) San Diego Padres: Moneyline

    The value is always a single line, so capture up to the next newline only.
    Anchoring at the start of a line keeps a label like "Play" from matching
    mid-text ("Top Play: ...").
    """
    m = re.search(rf"^{re.escape(label)}:\s*\n\s*([^\n]+)", block, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m2 = re.search(rf"^{re.escape(label)}:\s*([^\n]+)", block, re.MULTILINE)
    if m2:
        return m2.group(1).strip()
    return ""


def extract_analysis(block: str, play: str) -> str:
    """Return the pick's write-up, i.e. the text after the ``Play:`` value.

    Handles both layouts WagerTalk uses: the value on its own line after
    ``Play:`` (blank lines in between are fine) or on the same line as the
    label. In the first case the play line is skipped only when it equals the
    extracted play; if there is no play value, the analysis starts at its
    first line (nothing is eaten). Extraction stops at "Released/revised" or
    at the "Other Picks/Packages" promo section, either case.
    """
    m = re.search(r"^Play:[ \t]*([^\n]*)", block, re.MULTILINE)
    if not m:
        return ""
    inline_value = m.group(1).strip()
    lines = block[m.end():].split("\n")
    started = bool(inline_value)
    out = []
    for line in lines:
        if not started:
            if line.strip():
                started = True
                if line.strip() != play.strip():
                    out.append(line)
            continue
        if PROMO_RE.search(line):
            break
        out.append(line)
    return "\n".join(out).strip()


def parse_picks(text: str, experts: tuple[str, ...] = DEFAULT_EXPERTS) -> list[dict]:
    """Extract one dict per pick from the rendered page text.

    Each expert section is headed by a line like ``JIMMY ADAMS COLLEGE
    FOOTBALL`` (the site uppercases names via CSS, but matching is
    case-insensitive so a layout change cannot silently kill every pick).
    """
    picks: list[dict] = []
    pattern = re.compile(
        r"^(" + "|".join(re.escape(e) for e in experts) + r")\s+(.+?)$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(text))

    for i, match in enumerate(matches):
        raw_name = match.group(1)
        # Prefer the configured spelling of the name over the page's casing.
        name = next(
            (e for e in experts if e.lower() == raw_name.lower()), raw_name.title()
        )
        sport_raw = match.group(2).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        cut = re.search(r"^other\s+picks?\s*/\s*packages\b", block, re.IGNORECASE | re.MULTILINE)
        if cut:
            block = block[: cut.start()]

        event = extract_field(block, "Event")
        gametime = extract_field(block, "Date/Time")
        play = extract_field(block, "Play")
        rel_m = re.search(r"Released/revised\s+([^\n]+)", block)
        released = rel_m.group(1).strip() if rel_m else ""
        sport = sport_raw.title()
        analysis = extract_analysis(block, play)

        if not event and not play:
            continue

        picks.append(
            {
                "name": name,
                "sport": sport,
                "event": event,
                "gametime": gametime,
                "play": play,
                "analysis": analysis,
                "released": released,
                "profile_url": "https://www.wagertalk.com/profile/"
                + name.lower().replace(" ", "-"),
            }
        )
    return picks


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def card_html(p: dict, color: str) -> str:
    analysis_block = (
        '<div style="font-size:.82rem;color:#777;line-height:1.8;white-space:pre-wrap;margin-top:.5rem">'
        + esc(p["analysis"])
        + "</div>"
    ) if p["analysis"] else ""
    return (
        '<div style="background:#111318;border:1px solid #1a1d24;border-radius:10px;overflow:hidden;margin-bottom:1.25rem">'
        '<div style="display:flex;justify-content:space-between;align-items:center;padding:.8rem 1.1rem;border-bottom:1px solid #1a1d24">'
        f'<span style="font-size:.72rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:{color}">{esc(p["name"])}</span>'
        f'<span style="font-size:.66rem;background:#1a1d24;color:#4a5060;padding:2px 8px;border-radius:4px;text-transform:uppercase">{esc(p["sport"])}</span>'
        "</div>"
        '<div style="padding:1.1rem">'
        f'<div style="font-family:Georgia,serif;font-size:1.15rem;color:#e0dbd0;line-height:1.35;margin-bottom:.5rem">{esc(p["event"])}</div>'
        f'<div style="font-size:.73rem;color:#444;margin-bottom:.9rem">Game time: <strong style="color:#666">{esc(p["gametime"])}</strong></div>'
        f'<div style="background:#0c0e11;border:1px solid #1a1d24;border-left:3px solid {color};border-radius:5px;padding:.7rem .9rem;font-size:.9rem;font-weight:500;line-height:1.5">{esc(p["play"])}</div>'
        + analysis_block
        + "</div>"
        '<div style="padding:.55rem 1.1rem;border-top:1px solid #1a1d24;display:flex;justify-content:space-between;align-items:center">'
        f'<span style="font-size:.67rem;color:#333">{esc(p["released"])}</span>'
        f'<a href="{esc(p["profile_url"])}" target="_blank" style="font-size:.67rem;color:#3d4047;text-decoration:none">View profile -&gt;</a>'
        "</div>"
        "</div>"
    )


def build_html(
    picks: list[dict], fetched: str | None = None, experts: tuple[str, ...] = DEFAULT_EXPERTS
) -> str:
    fetched = fetched or datetime.now().strftime("%b %d, %Y %H:%M")
    label = " or ".join(experts)

    if not picks:
        body = f'<p style="color:#444;text-align:center;margin-top:4rem">No picks from {esc(label)} right now. Check back later.</p>'
    else:
        body = ""
        for p in picks:
            color = "#6aabf0" if "drew" in p["name"].lower() else "#74d48a"
            body += card_html(p, color)

    return (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'>\n"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>\n"
        "<meta http-equiv='refresh' content='7200'>\n"
        f"<title>WagerTalk - {' and '.join(experts)}</title>\n"
        "<style>\n"
        "body{font-family:'Segoe UI',sans-serif;background:#0c0e11;color:#ddd8ce;min-height:100vh;padding:2rem 1rem}\n"
        ".wrap{max-width:720px;margin:0 auto}\n"
        ".top{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid #1e2128;padding-bottom:.9rem;margin-bottom:2rem}\n"
        ".top h1{font-size:.85rem;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:#555}\n"
        ".ts{font-size:.72rem;color:#3d4047}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        "<div class='wrap'>\n"
        "  <div class='top'><h1>Drew Martin &amp; Jimmy Adams - Free Picks</h1><span class='ts'>Updated " + fetched + "</span></div>\n"
        + body
        + "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def git_push(repo_dir: str = REPO_DIR) -> None:
    print("Pushing to GitHub...", file=sys.stderr)
    os.chdir(repo_dir)
    subprocess.run(["git", "add", "docs/index.html"], check=True)
    result = subprocess.run(["git", "diff", "--staged", "--quiet"])
    if result.returncode != 0:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "commit", "-m", f"Update picks {timestamp}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Pushed.", file=sys.stderr)
    else:
        print("No changes to push.", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wagerpicks",
        description="Fetch WagerTalk free picks, parse them, and publish docs/index.html.",
    )
    parser.add_argument("--url", default=URL, help="page to scrape (default: %(default)s)")
    parser.add_argument(
        "--experts",
        default=",".join(DEFAULT_EXPERTS),
        help="comma-separated capper names (default: %(default)s)",
    )
    parser.add_argument("--out", default=OUT_PATH, help="output HTML path")
    parser.add_argument("--json", action="store_true", help="print picks as JSON, touch nothing")
    parser.add_argument("--dry-run", action="store_true", help="print HTML to stdout, touch nothing")
    parser.add_argument("--no-push", action="store_true", help="write the HTML but skip git push")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    experts = tuple(e.strip() for e in args.experts.split(",") if e.strip())
    if not experts:
        print("error: --experts must list at least one name", file=sys.stderr)
        return 2

    try:
        print("Fetching", args.url, file=sys.stderr)
        text = fetch_text(args.url)
        picks = parse_picks(text, experts=experts)
        print("Found", len(picks), "pick(s).", file=sys.stderr)

        if args.json:
            print(
                json.dumps(
                    {
                        "url": args.url,
                        "fetched_at": datetime.now().isoformat(timespec="seconds"),
                        "picks": picks,
                    },
                    indent=2,
                )
            )
            return 0

        html = build_html(picks, experts=experts)
        if args.dry_run:
            print(html)
            return 0

        out = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print("Written to", out, file=sys.stderr)

        if not args.no_push:
            git_push(REPO_DIR)
        return 0
    except Exception as exc:  # noqa: BLE001 - keep cron behaviour: report, exit 1
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
