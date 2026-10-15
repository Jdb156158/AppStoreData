"""Collect visible IOSMRR estimates through its public search form."""
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = 'https://iosmrr.com/?category=utilities'
PERIOD = 'DATA · SEP 2026'


def text(markup):
    return html.unescape(re.sub(r'<[^>]+>', '', markup)).strip()


def parse_page(markup):
    visible = re.sub(r'<script\b.*?</script>', '', markup, flags=re.S)
    if PERIOD not in text(visible):
        raise ValueError('IOSMRR period changed; do not mix snapshot months')
    rows = []
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', visible, re.S):
        cells = re.findall(r'<td\b[^>]*>(.*?)</td>', row, re.S)
        if len(cells) != 7:
            continue
        app_id = re.search(r'https://apps\.apple\.com/[^"\s]*?/id(\d+)["?]', cells[1])
        name = re.search(r'<span class="app-name">(.*?)</span>', cells[1], re.S)
        revenue = re.match(r'\$[\d,]+', text(cells[3]))
        downloads = text(cells[4])
        if app_id and name and revenue and re.fullmatch(r'[\d,]+', downloads):
            rows.append({'appId': app_id[1], 'name': text(name[1]), 'downloads': downloads, 'revenue': revenue[0]})
    return rows


def fetch_page(url):
    with urlopen(Request(url, headers={'User-Agent': 'AppStoreData/1.0'}), timeout=20) as response:
        rows = parse_page(response.read().decode())
    for row in rows:
        row['sourceUrl'] = url
    return rows


def fetch_app(app):
    for category in [{'category': 'utilities'}, {}]:
        url = 'https://iosmrr.com/?' + urlencode({**category, 'sort': 'revenue_desc', 'q': app['name']})
        row = next((row for row in fetch_page(url) if row['appId'] == app['id']), None)
        if row:
            return row
    return None


def main():
    apps = json.loads((ROOT / 'data/us-utilities.json').read_text())['apps']
    ids = {app['id'] for app in apps}
    rows = {row['appId']: row for row in fetch_page(SOURCE_URL) if row['appId'] in ids}
    remaining = [app for app in apps if app['id'] not in rows]
    unavailable = []
    print(f'Public category page: {len(rows)} / {len(apps)} matches', flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(fetch_app, app): app for app in remaining}
        for done, future in enumerate(as_completed(jobs), 1):
            app = jobs[future]
            try:
                row = future.result()
                if row:
                    rows[row['appId']] = row
                else:
                    unavailable.append({'appId': app['id'], 'name': app['name'], 'reason': 'Public search did not return the exact Apple ID'})
            except Exception as error:
                unavailable.append({'appId': app['id'], 'name': app['name'], 'reason': str(error)})
            if done % 10 == 0 or done == len(jobs):
                print(f'Searched {done} / {len(jobs)}; matched {len(rows)} / {len(apps)}', flush=True)
    snapshot = {
        'source': 'IOSMRR', 'sourceUrl': SOURCE_URL, 'periodLabel': PERIOD,
        'capturedAt': datetime.now(timezone.utc).isoformat(),
        'collectionMethod': 'Anonymous public HTML table and search form; exact Apple ID matching',
        'rows': [rows[app['id']] for app in apps if app['id'] in rows], 'unavailable': unavailable,
    }
    (ROOT / 'data/iosmrr-public-snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
