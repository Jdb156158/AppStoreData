"""Collect public US App Store star counts without account credentials."""
import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/star-ratings.json'


def parse_ratings(html):
    total_match = re.search(r'class=["\']rating-count["\'][^>]*>\s*([\d,]+)\s+Ratings?', html)
    matches = re.findall(r'class=["\']vote["\'][^>]*aria-label=["\']([1-5]) stars?,\s*([\d,]+) ratings?["\']', html)
    if not total_match or len(matches) != 5 or len({star for star, _ in matches}) != 5:
        raise ValueError('Apple did not return a complete five-star breakdown')
    total = int(total_match[1].replace(',', ''))
    stars = {star: int(value.replace(',', '')) for star, value in matches}
    if sum(stars.values()) != total:
        raise ValueError('Star counts do not match the total rating count')
    return {'total': total, 'byStar': [stars[str(star)] for star in range(1, 6)],
            'negative': sum(stars[str(star)] for star in (1, 2, 3))}


def collect_app(app_id):
    url = f'https://itunes.apple.com/us/customer-reviews/id{app_id}?displayable-kind=11'
    result = {'appId': str(app_id), 'country': 'us', 'sourceUrl': url, 'scope': 'current_cumulative',
              'capturedAt': datetime.now(timezone.utc).isoformat()}
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'X-Apple-Store-Front': '143441,12'})
    try:
        for attempt in range(2):
            try:
                with urlopen(request, timeout=25) as response:
                    html = response.read().decode('utf-8')
                break
            except HTTPError as exc:
                if attempt == 0 and exc.code in (403, 429, 500, 502, 503):
                    time.sleep(3)
                else:
                    raise
        return {**result, 'status': 'ok', **parse_ratings(html)}
    except Exception as exc:
        return {**result, 'status': 'unavailable', 'total': None, 'byStar': None, 'negative': None, 'error': str(exc)}


def collect(apps):
    result = {'schemaVersion': 1, 'country': 'us', 'scope': 'current_cumulative',
              'capturedAt': datetime.now(timezone.utc).isoformat(),
              'source': {'name': 'Apple App Store 美国区评星分布', 'authentication': 'none'},
              'note': '当前累计1–5星评星数量，包括无文字评星；不代表最近30天。Apple允许开发者重置摘要评分，因此不保证是上线至今累计。',
              'apps': {}}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(collect_app, app['id']): app for app in apps}
        for index, job in enumerate(as_completed(jobs), 1):
            sample = job.result()
            result['apps'][sample['appId']] = sample
            if index % 20 == 0 or index == len(apps):
                print(f'Star ratings: {index}/{len(apps)} applications collected', file=sys.stderr, flush=True)
    return result


def publish(data):
    import subprocess
    token = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s', 'appstoredata-sites-updater', '-a', 'appgprj_6acf47b372a481919d1f26c06488990f', '-w'], check=True, capture_output=True, text=True).stdout.strip()
    request = Request('https://us-utilities-top-200.carlgustav.chatgpt.site/api/star-ratings',
                      data=json.dumps(data, ensure_ascii=False).encode(), method='POST',
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    with urlopen(request, timeout=55) as response:
        receipt = json.load(response)
    if receipt.get('capturedAt') != data['capturedAt'] or receipt.get('count') != len(data['apps']):
        raise ValueError('Star ratings synchronization receipt does not match')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    apps = json.loads((ROOT / 'data/us-utilities.json').read_text())['apps']
    result = collect(apps)
    temporary = OUTPUT.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    temporary.replace(OUTPUT)
    if args.publish:
        publish(result)
    print(json.dumps({'applications': len(result['apps']), 'available': sum(app['status'] == 'ok' for app in result['apps'].values()), 'output': str(OUTPUT)}))


if __name__ == '__main__':
    main()
