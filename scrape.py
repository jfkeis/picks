#!/usr/bin/env python3
"""
WagerTalk scraper - Playwright with stealth settings to bypass bot detection
Writes docs/index.html for GitHub Pages
"""

import re, sys, os
from datetime import datetime


def fetch_text():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Run: pip install playwright && python3 -m playwright install chromium")
        sys.exit(1)

    print("Launching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        # Use a realistic browser context
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )

        # Hide the fact that we're running automation
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()

        # Visit Google first to look like a real referral
        page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1000)

        # Now go to WagerTalk
        page.goto("https://www.wagertalk.com/free-sports-picks", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(4000)

        text = page.inner_text("body")
        browser.close()

    return text


def extract_field(block, label):
    m = re.search(rf'{re.escape(label)}:\s*\n(.*?)(?:\n\n|\n(?=[A-Z]))', block, re.DOTALL)
    if m:
        return m.group(1).strip()
    m2 = re.search(rf'{re.escape(label)}:\s*(.+?)(?:\n|$)', block)
    if m2:
        return m2.group(1).strip()
    return ""


def parse_picks(text):
    picks = []
    pattern = re.compile(r'^(DREW MARTIN|JIMMY ADAMS)\s+(.+?)$', re.MULTILINE)
    matches = list(pattern.finditer(text))

    for i, match in enumerate(matches):
        name = match.group(1).title()
        sport_raw = match.group(2).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        cut = block.find("OTHER PICKS/PACKAGES")
        if cut != -1:
            block = block[:cut]

        event    = extract_field(block, "Event")
        gametime = extract_field(block, "Date/Time")
        play     = extract_field(block, "Play")

        analysis = ""
        play_pos = block.find("Play:\n")
        if play_pos != -1:
            after_play = block[play_pos + 6:]
            lines = after_play.split("\n")
            started = False
            analysis_lines = []
            for line in lines:
                if not started:
                    if line.strip():
                        started = True
                    continue
                if "Released/revised" in line:
                    break
                analysis_lines.append(line)
            analysis = "\n".join(analysis_lines).strip()

        rel_m    = re.search(r'Released/revised\s+(.*?)(?:\n|$)', block)
        released = rel_m.group(1).strip() if rel_m else ""
        sport    = sport_raw.title()

        if not event and not play:
            continue

        picks.append({
            "name": name,
            "sport": sport,
            "event": event,
            "gametime": gametime,
            "play": play,
            "analysis": analysis,
            "released": released,
            "profile_url": "https://www.wagertalk.com/profile/" + name.lower().replace(" ", "-"),
        })

    return picks


def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def build_html(picks):
    fetched = datetime.now().strftime("%b %d, %Y %H:%M UTC")

    if not picks:
        body = '<p style="color:#444;text-align:center;margin-top:4rem">No picks from Drew Martin or Jimmy Adams right now. Check back later.</p>'
    else:
        body = ""
        for p in picks:
            color = "#6aabf0" if "drew" in p["name"].lower() else "#74d48a"
            analysis_block = (
                '<div style="font-size:.82rem;color:#777;line-height:1.8;white-space:pre-wrap;margin-top:.5rem">'
                + esc(p["analysis"]) + '</div>'
            ) if p["analysis"] else ""

            body += (
                '<div style="background:#111318;border:1px solid #1a1d24;border-radius:10px;overflow:hidden;margin-bottom:1.25rem">'
                  '<div style="display:flex;justify-content:space-between;align-items:center;padding:.8rem 1.1rem;border-bottom:1px solid #1a1d24">'
                    '<span style="font-size:.72rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:' + color + '">' + esc(p["name"]) + '</span>'
                    '<span style="font-size:.66rem;background:#1a1d24;color:#4a5060;padding:2px 8px;border-radius:4px;text-transform:uppercase">' + esc(p["sport"]) + '</span>'
                  '</div>'
                  '<div style="padding:1.1rem">'
                    '<div style="font-family:Georgia,serif;font-size:1.15rem;color:#e0dbd0;line-height:1.35;margin-bottom:.5rem">' + esc(p["event"]) + '</div>'
                    '<div style="font-size:.73rem;color:#444;margin-bottom:.9rem">Game time: <strong style="color:#666">' + esc(p["gametime"]) + '</strong></div>'
                    '<div style="background:#0c0e11;border:1px solid #1a1d24;border-left:3px solid ' + color + ';border-radius:5px;padding:.7rem .9rem;font-size:.9rem;font-weight:500;line-height:1.5">' + esc(p["play"]) + '</div>'
                    + analysis_block +
                  '</div>'
                  '<div style="padding:.55rem 1.1rem;border-top:1px solid #1a1d24;display:flex;justify-content:space-between;align-items:center">'
                    '<span style="font-size:.67rem;color:#333">' + esc(p["released"]) + '</span>'
                    '<a href="' + esc(p["profile_url"]) + '" target="_blank" style="font-size:.67rem;color:#3d4047;text-decoration:none">View profile -&gt;</a>'
                  '</div>'
                '</div>'
            )

    return (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'>\n"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>\n"
        "<meta http-equiv='refresh' content='7200'>\n"
        "<title>WagerTalk - Drew Martin and Jimmy Adams</title>\n"
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
        + body +
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def main():
    URL = "https://www.wagertalk.com/free-sports-picks"
    print("Fetching", URL)
    text = fetch_text()

    print("--- Page sample (chars 1500-2500) ---")
    print(text[1500:2500])
    print("--------------------------------------")

    picks = parse_picks(text)
    print("Found", len(picks), "pick(s).")
    html = build_html(picks)

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Written to docs/index.html")


if __name__ == "__main__":
    main()
