"""Save available worldwide last-month summaries using the official, signed-in CLI."""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
CLI = ['pnpm', '--package=@appfigures/cli@4.0.0', 'dlx', 'af']


def reviewed_row(item, app_id):
    unified = item.get('unified_app') or {}
    products = unified.get('member_products', [])
    product = next((p for p in products if str(p.get('vendor_identifier')) == app_id and 'apple:ios' in p.get('storefronts', [])), None)
    if product is None:
        return None
    downloads, revenue = item.get('downloads_estimate') or {}, item.get('revenue_estimate') or {}
    periods = {(e.get('start_date'), e.get('end_date')) for e in (downloads, revenue) if e.get('value') is not None}
    if not periods:
        return None
    if len(periods) != 1 or any(e.get('countries') for e in (downloads, revenue)):
        raise ValueError(f'{app_id}: summary period or worldwide scope is inconsistent')
    start, end = periods.pop()
    if not start or not end or start[:7] != end[:7] or revenue.get('currency_code', 'USD') != 'USD':
        raise ValueError(f'{app_id}: summary month or currency is not verified')
    return {
        'appId': app_id, 'productId': product['id'], 'unifiedAppId': unified['id'],
        'name': product['name'], 'month': start[:7], 'startDate': start, 'endDate': end,
        'storefronts': sorted({s for p in products for s in p.get('storefronts', [])}),
        'downloadsMonthly': float(downloads['value']) if downloads.get('value') is not None else None,
        'downloadsBound': downloads.get('value_constraint'),
        'revenueMonthlyUSD': float(revenue['value']) if revenue.get('value') is not None else None,
        'revenueBound': revenue.get('value_constraint'),
        'sourceUrl': f"https://appfigures.com/reports/app-profile/{unified['id']}",
        'rawSummary': item,
    }


def fetch_app(app):
    for query in dict.fromkeys([app['name'], app['name'].split(':')[0]]):
        path = '/unified-apps/search?' + urlencode({'q': query, 'count': 50, 'expand': 'unified-app,product,estimates'})
        response = subprocess.run(CLI + ['api', path], capture_output=True, text=True, timeout=90)
        if response.returncode:
            return None, {'appId': app['id'], 'reason': response.stderr.strip()}
        payload = json.loads(response.stdout)
        rows = [row for item in payload['results'] if (row := reviewed_row(item, app['id'])) is not None]
        if len(rows) == 1:
            return rows[0], None
    return None, {'appId': app['id'], 'reason': f'Exact Apple App ID matches: {len(rows)}'}


if __name__ == '__main__':
    apps = json.loads((ROOT / 'data/us-utilities.json').read_text())['apps']
    rows, unavailable = [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for app, (row, error) in zip(apps, pool.map(fetch_app, apps)):
            if row is not None:
                rows.append(row)
            else:
                unavailable.append(error)
            print(f"{app['id']}: {'matched' if row else error['reason']}", flush=True)
    snapshot = {
        'source': 'Appfigures', 'sourceUrl': 'https://github.com/appfigures/cli',
        'capturedAt': datetime.now(timezone.utc).isoformat(), 'country': 'worldwide', 'currency': 'USD',
        'collectionMethod': 'Official CLI 4.0.0: unified-apps/search with estimates expansion; exact Apple App ID match.',
        'note': 'Previous calendar month, worldwide unified-app summary. May combine iOS and Android; storefronts retained per row. Revenue is after platform fees. Bounds are excluded from averages. No US detail or historical estimates requested.',
        'rows': rows, 'unavailable': unavailable,
    }
    (ROOT / 'data/appfigures-public-snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f'Saved {len(rows)} / {len(apps)} Appfigures summaries')
