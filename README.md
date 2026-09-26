# picks

Free picks from [wagertalk.com/free-sports-picks](https://www.wagertalk.com/free-sports-picks),
filtered for selected experts (Drew Martin and Jimmy Adams by default), rendered
as a static page on GitHub Pages and refreshed on a schedule.

Pick pages on WagerTalk are JavaScript-rendered, so the scraper drives a real
(headless) Chromium via Playwright, reads the rendered page text, and parses it
into structured picks:

| Field | Source on the page |
| --- | --- |
| `name` | expert section header (case-insensitive, `--experts` to change) |
| `sport` | the text after the expert's name on the header line |
| `event` | the `Event:` line, e.g. `(909) Arizona Diamondbacks at (910) San Diego Padres: Moneyline` |
| `gametime` | the `Date/Time:` line |
| `play` | the `Play:` line |
| `analysis` | the write-up after the play, up to `Released/revised` or the `Other Picks/Packages` promo section |
| `released` | the `Released/revised` line |
| `profile_url` | built from the expert's name |

The parser is a pure-text module with no browser dependency — the whole
pipeline except the network fetch runs offline in the test suite.

## Requirements

- Python 3.9+
- `playwright` + a Chromium install for the live fetch
  (`pip install playwright && python3 -m playwright install chromium`)

## Usage

```bash
python3 scrape.py                        # fetch, write docs/index.html, git push
python3 scrape.py --dry-run              # print the HTML instead, touch nothing
python3 scrape.py --json                 # print parsed picks as JSON, touch nothing
python3 scrape.py --no-push              # write docs/index.html but skip git push
python3 scrape.py --experts "A,B"        # track other cappers
python3 scrape.py --url URL --out PATH   # override source / output
```

| Flag | Purpose |
| --- | --- |
| `--url` | page to scrape (default: the free-sports-picks page) |
| `--experts` | comma-separated capper names (default `Drew Martin,Jimmy Adams`) |
| `--out` | where to write the HTML (default `docs/index.html`) |
| `--json` | print the picks as JSON and exit — no writes, no push |
| `--dry-run` | print the HTML to stdout and exit — no writes, no push |
| `--no-push` | write the HTML but skip `git push` |

Progress messages go to stderr, so `--dry-run > out.html` and `--json | jq`
produce clean output.

Exit codes: `0` success, `1` fetch/parse error, `2` bad arguments.

## Automated refresh

The page is designed to be refreshed on a schedule (the repo's
`.github/workflows/scrape.yml` shows the original GitHub Actions version; it is
currently disabled in favour of a cron job). `--no-push` is handy on machines
that are not clones of this repository: write the page wherever you serve it
from without the git half.

The generated page auto-refreshes every two hours
(`<meta http-equiv='refresh' content='7200'>`), so even a static host stays
fresh between scrapes.

## Development

```bash
pip install -e ".[dev]"
pytest          # offline, no browser needed
ruff check .
```

The tests cover the parser against fixtures taken from the live page and from
a real committed `docs/index.html`, plus the CLI (dry-run / json / no-push /
custom experts), HTML escaping, and the git publish step (subprocess mocked).

## License

MIT. See [LICENSE](LICENSE).