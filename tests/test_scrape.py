"""Offline tests for scrape.py — nothing here touches the network or a browser.

Fixtures are built from the real WagerTalk page (fetched 2026-09-26) and from
the last committed docs/index.html, so the expected values below are the
actual values the scraper produced against the live site.
"""

import json
import types

import pytest

import scrape

# ---------------------------------------------------------------------------
# Fixtures — real page data, laid out the way browser innerText renders it
# (labels and values on separate lines, blank lines between them, expert
# names uppercased by the site's CSS text-transform).
# ---------------------------------------------------------------------------

JIMMY_ANALYSIS = (
    "The hype is real in Starkville, where Mississippi State came back from a major 1st half "
    "deficit to get the win last week in Columbia. Kamario Taylor has quickly become "
    "recognized as one of the best QB's in the nation and the cowbells will be loud when Mizzou "
    "comes to town. The betting market has been dead wrong about this team all season, as many "
    "believed Minnesota was the right side two weeks back. The result was a 38-13 beatdown by "
    "the Bulldogs, who are averaging 47 ppg and an amazing 7.86 yards per play on offense. As "
    "for Missouri, they were outgained 323-230 last week on their own home field to Troy, who "
    "really gave Eli Drinkwitz some trouble. Although the Tigers were able to escape with the "
    "win, it will be awfully difficult for them to stay within a touchdown in this environment "
    "against the better team. Take Mississippi State.\n\n"
    "DON'T MISS JIMMY'S 5% CFB TOP PLAY TODAY!"
)

DREW_ANALYSIS = (
    "The hottest team in baseball is just one game out of the postseason with two games to "
    "play. The Diamondbacks are hotter than an Arizona desert snake winning 6 straight games, "
    "combine that with the Phillies losing three straight and we have ourselves a tight race in "
    "the final weekend of the regular season. Ride the Snakes in this one. Bet Arizona.\n\n"
    "12-1 (92%) College Football run (+52% PROFIT).\n\n"
    "20-6 (77%) All 5% picks (66% PROFIT).\n\n"
    "#1 Ranked All Sports Handicapper Overall L 365 Days (Return On Investment)."
)

REAL_PAGE = """\
JIMMY ADAMS COLLEGE FOOTBALL

View profile

Event:

(375) Missouri at (376) Mississippi State: Spread

Date/Time:

September 26, 2026 7:45 PM EDT

Play:

Mississippi State -5.5 (-110)

The hype is real in Starkville, where Mississippi State came back from a major 1st half deficit to get the win last week in Columbia. Kamario Taylor has quickly become recognized as one of the best QB's in the nation and the cowbells will be loud when Mizzou comes to town. The betting market has been dead wrong about this team all season, as many believed Minnesota was the right side two weeks back. The result was a 38-13 beatdown by the Bulldogs, who are averaging 47 ppg and an amazing 7.86 yards per play on offense. As for Missouri, they were outgained 323-230 last week on their own home field to Troy, who really gave Eli Drinkwitz some trouble. Although the Tigers were able to escape with the win, it will be awfully difficult for them to stay within a touchdown in this environment against the better team. Take Mississippi State.

DON'T MISS JIMMY'S 5% CFB TOP PLAY TODAY!

Released/revised 10 hour(s) ago

Other Picks/Packages

NFL SUN 5-PACK! 75% (6-2) RUN! : $29.00

Add to Cart

Guaranteed

How Our Pick Guarantee Works

DREW MARTIN MAJOR LEAGUE BASEBALL

View profile

Event:

(909) Arizona Diamondbacks at (910) San Diego Padres: Moneyline

Date/Time:

September 26, 2026 8:40 PM EDT

Play:

Arizona Diamondbacks 106 Action

The hottest team in baseball is just one game out of the postseason with two games to play. The Diamondbacks are hotter than an Arizona desert snake winning 6 straight games, combine that with the Phillies losing three straight and we have ourselves a tight race in the final weekend of the regular season. Ride the Snakes in this one. Bet Arizona.

12-1 (92%) College Football run (+52% PROFIT).

20-6 (77%) All 5% picks (66% PROFIT).

#1 Ranked All Sports Handicapper Overall L 365 Days (Return On Investment).

Released/revised 15 hour(s) ago

Other Picks/Packages

*12-1 (92%) CFB HEATER #1 SATURDAY NIGHT CASH $$: $25.00

Add to Cart

How Our Pick Guarantee Works

Bill "Krackman" KrackombergerCollege Football

View profile

Event:

(367) Air Force at (368) Nevada: Spread

Date/Time:

September 26, 2026 10:30 PM EDT

Play:

Nevada +5.5 (-110)

Ok with +6 -115

Released/revised 2 day(s) ago

Other Picks/Packages

NFL SUNDAY BEST BET 4%: $25.00

Add to Cart

Cappers

Ben Burns

Jimmy Adams

Drew Martin

Bill Krackman
"""

SINGLE_PICK = """\
JIMMY ADAMS COLLEGE FOOTBALL

View profile

Event:

(375) Missouri at (376) Mississippi State: Spread

Date/Time:

September 26, 2026 7:45 PM EDT

Play:

Mississippi State -5.5 (-110)

The hype is real in Starkville.

Released/revised 10 hour(s) ago

Other Picks/Packages

NFL SUN 5-PACK! : $29.00
"""


# ---------------------------------------------------------------------------
# parse_picks — against the real page
# ---------------------------------------------------------------------------


def test_parse_real_page_two_picks():
    picks = scrape.parse_picks(REAL_PAGE)
    assert len(picks) == 2
    jimmy, drew = picks

    assert jimmy["name"] == "Jimmy Adams"
    assert jimmy["sport"] == "College Football"
    assert jimmy["event"] == "(375) Missouri at (376) Mississippi State: Spread"
    assert jimmy["gametime"] == "September 26, 2026 7:45 PM EDT"
    assert jimmy["play"] == "Mississippi State -5.5 (-110)"
    assert jimmy["released"] == "10 hour(s) ago"
    assert jimmy["profile_url"] == "https://www.wagertalk.com/profile/jimmy-adams"
    # Promo section is cut: the price line never reaches the analysis.
    assert "$29.00" not in jimmy["analysis"]
    assert "NFL SUN 5-PACK" not in jimmy["analysis"]
    assert jimmy["analysis"] == JIMMY_ANALYSIS

    assert drew["name"] == "Drew Martin"
    assert drew["sport"] == "Major League Baseball"
    assert drew["event"] == "(909) Arizona Diamondbacks at (910) San Diego Padres: Moneyline"
    assert drew["gametime"] == "September 26, 2026 8:40 PM EDT"
    assert drew["play"] == "Arizona Diamondbacks 106 Action"
    assert drew["released"] == "15 hour(s) ago"
    assert drew["profile_url"] == "https://www.wagertalk.com/profile/drew-martin"
    assert drew["analysis"] == DREW_ANALYSIS


def test_parse_real_page_ignores_other_experts_and_footer():
    # Krackman's section and the footer capper list must not add picks.
    picks = scrape.parse_picks(REAL_PAGE)
    assert [p["name"] for p in picks] == ["Jimmy Adams", "Drew Martin"]


def test_parse_case_insensitive_names():
    text = REAL_PAGE.replace("JIMMY ADAMS", "jimmy adams").replace(
        "DREW MARTIN", "Drew Martin"
    )
    picks = scrape.parse_picks(text)
    assert len(picks) == 2
    # Configured spelling wins over the page's casing.
    assert picks[0]["name"] == "Jimmy Adams"
    assert picks[1]["name"] == "Drew Martin"


def test_parse_empty_text():
    assert scrape.parse_picks("") == []
    assert scrape.parse_picks("no experts here at all\n") == []


def test_parse_drops_pick_with_no_event_and_no_play():
    text = SINGLE_PICK.replace("Event:\n\n(375) Missouri at (376) Mississippi State: Spread\n\n", "")
    text = text.replace("Play:\n\nMississippi State -5.5 (-110)\n\n", "")
    assert scrape.parse_picks(text) == []


def test_parse_two_picks_same_expert():
    text = SINGLE_PICK + "\n\nJIMMY ADAMS NFL\n\nEvent:\n\nC vs D\n\nPlay:\n\nOver 40\n\nReleased/revised 2 hour(s) ago\n"
    picks = scrape.parse_picks(text)
    assert len(picks) == 2
    assert picks[0]["event"] == "(375) Missouri at (376) Mississippi State: Spread"
    assert picks[1]["event"] == "C vs D"
    assert picks[1]["play"] == "Over 40"


def test_parse_custom_experts():
    text = "BEN BURNS CFL\n\nEvent:\n\nA at B\n\nPlay:\n\nEdmonton -8.5\n\nReleased/revised 1 hour(s) ago\n"
    picks = scrape.parse_picks(text, experts=("Ben Burns",))
    assert len(picks) == 1
    assert picks[0]["name"] == "Ben Burns"
    assert picks[0]["sport"] == "Cfl"


# ---------------------------------------------------------------------------
# extract_field
# ---------------------------------------------------------------------------


def test_extract_field_blank_line_layout():
    block = "Event:\n\n(909) Arizona Diamondbacks at (910) San Diego Padres: Moneyline\n\nDate/Time:\n\nlater"
    assert scrape.extract_field(block, "Event") == "(909) Arizona Diamondbacks at (910) San Diego Padres: Moneyline"
    assert scrape.extract_field(block, "Date/Time") == "later"


def test_extract_field_same_line_layout():
    assert scrape.extract_field("Event: A at B\n", "Event") == "A at B"
    assert scrape.extract_field("Event: ", "Event") == ""


def test_extract_field_value_with_colons():
    block = "Event:\n\n(909) A at (910) B: Moneyline\n"
    assert scrape.extract_field(block, "Event") == "(909) A at (910) B: Moneyline"


def test_extract_field_missing():
    assert scrape.extract_field("Date/Time:\n\nSept 26\n", "Play") == ""


def test_extract_field_anchored_to_line_start():
    # A label appearing mid-line ("Top Play: ...") must not shadow the real one.
    block = "DON'T MISS JIMMY'S 5% CFB TOP PLAY TODAY!\n\nPlay:\n\nMississippi State -5.5 (-110)\n"
    assert scrape.extract_field(block, "Play") == "Mississippi State -5.5 (-110)"
    # Same defence against the analysis text mentioning a label.
    block2 = "Some analysis with Event: mentioned inside\n\nEvent:\n\nThe Real Event\n"
    assert scrape.extract_field(block2, "Event") == "The Real Event"


def test_extract_field_play_ends_at_first_newline():
    # A lowercase start to the next line must not swallow the value (old regex
    # would keep capturing because neither \n\n nor \n[A-Z] stopped it).
    block = "Play:\nRams -3.5\nhot take but the market disagrees\n"
    assert scrape.extract_field(block, "Play") == "Rams -3.5"


# ---------------------------------------------------------------------------
# extract_analysis
# ---------------------------------------------------------------------------


def test_analysis_skips_only_the_play_line():
    block = "Play:\n\nMississippi State -5.5 (-110)\n\nThe hype is real.\n\nReleased/revised 10 hour(s) ago\n"
    assert scrape.extract_analysis(block, "Mississippi State -5.5 (-110)") == "The hype is real."


def test_analysis_keeps_first_line_when_play_missing():
    # Old code always dropped the first non-blank line; with no play value that
    # was the first analysis sentence — data loss.
    block = "Play:\n\nThe hype is real.\n\nReleased/revised 1 hour(s) ago\n"
    assert scrape.extract_analysis(block, "") == "The hype is real."


def test_analysis_keeps_first_line_when_play_not_the_leading_text():
    # "Play:" label with the value on the same line, then analysis: nothing to skip.
    block = "Play: Rams -3.5\n\nThe hype is real.\n"
    assert scrape.extract_analysis(block, "Rams -3.5") == "The hype is real."


def test_analysis_stops_at_released_case_insensitive():
    block = "Play:\n\nX\n\ntext one\n\ntext two\n\nRELEASED/REVISED 2 hour(s) ago\n\njunk\n"
    assert scrape.extract_analysis(block, "X") == "text one\n\ntext two"


def test_analysis_stops_at_other_picks_case_insensitive():
    # No "Released/revised" line at all: the promo section must still be cut
    # (old code only cut the literal "OTHER PICKS/PACKAGES" — never matched
    # the real "Other Picks/Packages" — and leaked promo text into analysis).
    block = "Play:\n\nMississippi State -5.5 (-110)\n\nThe hype is real.\n\nOther Picks/Packages\n\nNFL 5-PACK: $29.00\n\nAdd to Cart\n"
    assert scrape.extract_analysis(block, "Mississippi State -5.5 (-110)") == "The hype is real."


def test_analysis_missing_play_label():
    assert scrape.extract_analysis("no play here\n", "whatever") == ""


def test_analysis_preserves_internal_blank_lines():
    block = "Play:\n\nArizona 106 Action\n\nFirst para.\n\nSecond para.\n\nReleased/revised 15 hour(s) ago\n"
    assert scrape.extract_analysis(block, "Arizona 106 Action") == "First para.\n\nSecond para."


# ---------------------------------------------------------------------------
# esc / build_html
# ---------------------------------------------------------------------------


def test_esc():
    assert scrape.esc('& < > "\'') == "&amp; &lt; &gt; &quot;&#39;"


def test_build_html_empty_picks():
    html = scrape.build_html([], fetched="Sep 26, 2026 22:00")
    assert "<!DOCTYPE html>" in html
    assert "No picks from Drew Martin or Jimmy Adams right now. Check back later." in html
    assert "Updated Sep 26, 2026 22:00" in html


def test_build_html_renders_real_picks():
    picks = scrape.parse_picks(REAL_PAGE)
    html = scrape.build_html(picks, fetched="Sep 26, 2026 22:00")
    assert "<title>WagerTalk - Drew Martin and Jimmy Adams</title>" in html
    assert "Drew Martin &amp; Jimmy Adams - Free Picks" in html
    assert "Mississippi State -5.5 (-110)" in html  # play, escaped-inert
    assert DREW_ANALYSIS in html
    # Drew's card uses the blue accent, Jimmy's the green one.
    drew_idx = html.find("Arizona Diamondbacks 106 Action")
    assert html.rfind("#6aabf0", 0, drew_idx) > html.rfind("#74d48a", 0, drew_idx)
    assert 'href="https://www.wagertalk.com/profile/drew-martin"' in html


def test_build_html_escapes_pick_content():
    pick = {
        "name": "A & B",
        "sport": 'S"PORT',
        "event": "<E>",
        "gametime": "now",
        "play": "X'Y",
        "analysis": "",
        "released": "1 hour(s) ago",
        "profile_url": "https://example.com/p?a=1&b=2",
    }
    html = scrape.build_html([pick], fetched="now")
    assert "A &amp; B" in html
    assert "&lt;E&gt;" in html
    assert "S&quot;PORT" in html
    assert "X&#39;Y" in html
    assert "example.com/p?a=1&amp;b=2" in html
    # Every ampersand in the output must be part of an entity.
    assert html.count("&") == html.count("&amp;") + html.count("&lt;") + html.count("&gt;") + html.count("&quot;") + html.count("&#39;")


def test_build_html_omits_analysis_block_when_empty():
    pick = {
        "name": "Drew Martin",
        "sport": "MLB",
        "event": "E",
        "gametime": "G",
        "play": "P",
        "analysis": "",
        "released": "R",
        "profile_url": "U",
    }
    html = scrape.build_html([pick])
    assert "white-space:pre-wrap" not in html


def test_build_html_custom_experts_title():
    html = scrape.build_html([], fetched="now", experts=("Ben Burns",))
    assert "No picks from Ben Burns right now. Check back later." in html
    assert "<title>WagerTalk - Ben Burns</title>" in html


# ---------------------------------------------------------------------------
# CLI — main()
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_fetch(monkeypatch):
    def _fake(fetch_return=SINGLE_PICK, fetch_error=None):
        calls = {}

        def fetch(url):
            calls["url"] = url
            if fetch_error:
                raise fetch_error
            return fetch_return

        monkeypatch.setattr(scrape, "fetch_text", fetch)
        return calls

    return _fake


def test_cli_json(fake_fetch, tmp_path, capsys):
    out = tmp_path / "never.json"
    fake_fetch()
    assert scrape.main(["--json", "--out", str(out)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["url"] == scrape.URL
    assert len(data["picks"]) == 1
    assert data["picks"][0]["name"] == "Jimmy Adams"
    assert not out.exists()  # --json touches nothing


def test_cli_json_stdout_is_pure_json(fake_fetch, capsys):
    fake_fetch()
    scrape.main(["--json"])
    captured = capsys.readouterr()
    json.loads(captured.out)  # must parse cleanly — no progress noise on stdout
    assert "Fetching" in captured.err  # progress goes to stderr


def test_cli_dry_run(fake_fetch, tmp_path, capsys):
    out = tmp_path / "never.html"
    fake_fetch()
    assert scrape.main(["--dry-run", "--out", str(out)]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("<!DOCTYPE html>")
    assert "Mississippi State -5.5 (-110)" in captured.out
    assert not out.exists()


def test_cli_write_no_push(fake_fetch, tmp_path):
    out = tmp_path / "index.html"
    fake_fetch()
    assert scrape.main(["--no-push", "--out", str(out)]) == 0
    assert out.exists()
    assert "Mississippi State -5.5 (-110)" in out.read_text(encoding="utf-8")


def test_cli_url_passthrough(fake_fetch):
    calls = fake_fetch()
    scrape.main(["--dry-run", "--url", "https://example.com/feed"])
    assert calls["url"] == "https://example.com/feed"


def test_cli_custom_experts(fake_fetch, capsys):
    text = "BEN BURNS CFL\n\nEvent:\n\nA at B\n\nPlay:\n\nEdmonton -8.5\n\nReleased/revised 1 hour(s) ago\n"
    fake_fetch(fetch_return=text)
    assert scrape.main(["--dry-run", "--experts", "Ben Burns"]) == 0
    assert "Edmonton -8.5" in capsys.readouterr().out


def test_cli_empty_experts(fake_fetch, capsys):
    assert scrape.main(["--experts", " , "]) == 2
    assert "at least one name" in capsys.readouterr().err


def test_cli_unknown_flag(fake_fetch):
    with pytest.raises(SystemExit) as exc:
        scrape.main(["--nope"])
    assert exc.value.code == 2


def test_cli_fetch_error_returns_1(fake_fetch, capsys):
    fake_fetch(fetch_error=RuntimeError("boom"))
    assert scrape.main([]) == 1
    assert "boom" in capsys.readouterr().err


def test_cli_full_pipeline_writes_and_pushes(fake_fetch, tmp_path):
    out = tmp_path / "index.html"
    ran = []

    def fake_git_push(repo_dir):
        ran.append(repo_dir)

    fake_fetch()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(scrape, "git_push", fake_git_push)
    try:
        assert scrape.main(["--out", str(out)]) == 0
    finally:
        monkeypatch.undo()
    assert out.exists()
    assert ran == [scrape.REPO_DIR]


# ---------------------------------------------------------------------------
# git_push
# ---------------------------------------------------------------------------


def _git_run_fake(returncodes):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        code = returncodes.pop(0) if isinstance(returncodes, list) else returncodes
        return types.SimpleNamespace(returncode=code)

    return calls, run


def test_git_push_no_changes(monkeypatch, capsys):
    calls, run = _git_run_fake(0)  # git diff --staged --quiet exits 0 = no changes
    monkeypatch.setattr(scrape.subprocess, "run", run)
    scrape.git_push("/tmp")
    assert [" ".join(c) for c in calls] == ["git add docs/index.html", "git diff --staged --quiet"]
    assert "No changes to push." in capsys.readouterr().err


def test_git_push_with_changes_commits_and_pushes(monkeypatch):
    calls, run = _git_run_fake([0, 1, 0, 0])
    monkeypatch.setattr(scrape.subprocess, "run", run)
    scrape.git_push("/tmp")
    commands = [" ".join(c) for c in calls]
    assert commands[0] == "git add docs/index.html"
    assert commands[1] == "git diff --staged --quiet"
    assert commands[2].startswith("git commit -m Update picks")
    assert commands[3] == "git push"
