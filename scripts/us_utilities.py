"""Fetch the US Utilities Top Grossing feed without account credentials."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
CHART_URL = 'https://itunes.apple.com/WebObjects/MZStore.woa/wa/viewTop?genreId=6002&popId=38'
CHART_SIZE = 200


def get_json(url, headers=None):
    request = Request(url, headers={'User-Agent': 'AppStoreData/1.0', 'Accept': 'application/json', **(headers or {})})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def normalize(chart_response, metadata=None, as_of=None):
    page = chart_response['pageData']['segmentedControl']['segments'][0]['pageData']
    chart = page['selectedChart']
    if chart['id'] != '38' or 'Top Grossing' not in chart['title'] or page['metricsBase']['storeFrontHeader'] != '143441,29':
        raise ValueError('Apple 返回的榜单不是美区工具畅销榜')
    ids = [str(app_id) for app_id in chart['adamIds']]
    if len(ids) != CHART_SIZE or page['genre']['id'] != '6002':
        raise ValueError('榜单数量或工具分类与预期不符')
    if len(set(ids)) != CHART_SIZE:
        raise ValueError('榜单包含重复应用')
    lockups = chart_response['storePlatformData']['lockup']['results']
    details = {str(app['trackId']): app for app in (metadata or {}).get('results', [])}
    today = as_of or datetime.now(timezone(timedelta(hours=8))).date()
    previous_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    apps = []
    for rank, app_id in enumerate(ids, 1):
        extra = details.get(app_id, {})
        lockup = lockups.get(app_id, {})
        artwork = lockup.get('artwork', {}).get('url', '').replace('{w}', '100').replace('{h}', '100').replace('{f}', 'jpg')
        offer = next(iter(lockup.get('offers', [])), {})
        apps.append({
            'rank': rank, 'id': app_id, 'name': extra.get('trackName') or lockup.get('name') or f'应用 {app_id}',
            'developer': extra.get('artistName') or lockup.get('artistName'), 'bundleId': extra.get('bundleId'),
            'icon': extra.get('artworkUrl100') or artwork,
            'url': extra.get('trackViewUrl') or lockup.get('url') or f'https://apps.apple.com/us/app/id{app_id}', 'category': page['genre']['name'],
            'price': extra.get('price', offer.get('price')), 'currency': extra.get('currency', 'USD'),
            'rating': extra.get('averageUserRating'), 'ratingCount': extra.get('userRatingCount'),
            'version': extra.get('version') or offer.get('version', {}).get('display'), 'updatedAt': extra.get('currentVersionReleaseDate'),
            'releasedAt': extra.get('releaseDate') or lockup.get('releaseDate'),
            'downloadsLifetime': None, 'downloadsLastMonth': None,
            'revenueLifetimeUSD': None, 'revenueLastMonthUSD': None,
        })
    return {
        'source': 'Apple iTunes Top Charts', 'sourceUrl': chart['seeAllUrl'], 'country': 'us', 'categoryId': '6002',
        'chart': 'topgrossingapplications', 'feedTitle': chart['title'],
        'feedUpdatedAt': None, 'capturedAt': datetime.now(timezone.utc).isoformat(),
        'metadataSource': 'Apple iTunes Lookup', 'apps': apps,
        'commercialMetrics': {
            'country': 'us', 'month': previous_month, 'currency': 'USD',
            'source': None, 'status': 'unavailable',
            'note': '下载量与收入接受第三方估算；当前尚未取得符合美国区、历史累计及上个自然月口径的数据。待获取不代表零。',
        },
    }


def fetch_rank():
    raw = get_json(CHART_URL, {'X-Apple-Store-Front': '143441,29'})
    normalize(raw)
    ids = ','.join(raw['pageData']['segmentedControl']['segments'][0]['pageData']['selectedChart']['adamIds'])
    lookup_url = 'https://itunes.apple.com/lookup?' + urlencode({'id': ids, 'country': 'us', 'limit': CHART_SIZE})
    metadata = None
    try:
        metadata = get_json(lookup_url)
    except (URLError, TimeoutError):
        pass  # The ranking remains valid if optional metadata is temporarily unavailable.
    result = normalize(raw, metadata)
    attach_public_estimates(result)
    result['metadataSourceUrl'] = lookup_url
    (ROOT / 'data/apple-us-utilities-chart-raw.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2))
    if metadata is not None:
        (ROOT / 'data/apple-us-utilities-lookup.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    (ROOT / 'data/us-utilities.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def attach_public_estimates(result):
    """Join a reviewed public-page snapshot by App ID, never by rank or name."""
    snapshot = json.loads((ROOT / 'data/iosmrr-public-snapshot.json').read_text())
    if snapshot['source'] != 'IOSMRR' or snapshot['periodLabel'] != 'DATA · SEP 2026':
        raise ValueError('公开估算来源或月份未核实')
    rows = {row['appId']: row for row in snapshot['rows']}
    if len(rows) != len(snapshot['rows']):
        raise ValueError('公开估算包含重复 App ID')
    for app in result['apps']:
        row = rows.get(app['id'])
        app['publicEstimate'] = None if row is None else {
            'downloadsMonthly': int(row['downloads'].replace(',', '')),
            'estimatedMRRUSD': int(row['revenue'].removeprefix('$').replace(',', '')),
        }
    result['publicMetrics'] = {
        'source': snapshot['source'], 'sourceUrl': snapshot['sourceUrl'],
        'periodLabel': snapshot['periodLabel'], 'month': '2026-09',
        'capturedAt': snapshot['capturedAt'], 'country': None, 'currency': 'USD',
        'collectionMethod': '匿名网页可见表格快照，按 App ID 匹配；不是实时 API。',
        'note': '来源标记 2026-09；地区、计算方法及税费口径未披露。收入字段原名 Est. MRR，不等同于已核实的当月总收入。刷新按钮仅更新 Apple 榜单，估算仍为保存的快照。',
        'coverage': sum(app['publicEstimate'] is not None for app in result['apps']),
    }
    result['sensorTowerMetrics'] = json.loads((ROOT / 'data/sensortower-public-snapshot.json').read_text())
    sensor_rows = {row['appId']: row for row in result['sensorTowerMetrics']['rows']}
    result['appfiguresMetrics'] = json.loads((ROOT / 'data/appfigures-public-snapshot.json').read_text())
    appfigures_rows = {row['appId']: row for row in result['appfiguresMetrics']['rows']}
    if len(appfigures_rows) != len(result['appfiguresMetrics']['rows']):
        raise ValueError('Appfigures 估算包含重复 App ID')
    result['appfiguresMetrics']['coverage'] = sum(app['id'] in appfigures_rows for app in result['apps'])
    qimai = json.loads((ROOT / 'data/qimai-public-snapshot.json').read_text())
    if qimai['source'] != '七麦数据' or qimai['country'] != 'us' or qimai['periodLabel'] != '昨日':
        raise ValueError('七麦来源、地区或日度口径未核实')
    qimai_rows = {row['appId']: row for row in qimai['rows']}
    if len(qimai_rows) != len(qimai['rows']) or any(row['country'] != 'us' or row['periodLabel'] != '昨日' for row in qimai_rows.values()):
        raise ValueError('七麦包含重复 App ID 或不一致口径')
    qimai['coverage'] = sum(app['id'] in qimai_rows for app in result['apps'])
    result['qimaiMetrics'] = qimai
    appmagic = json.loads((ROOT / 'data/appmagic-monthly-public-snapshot.json').read_text())
    if appmagic['source'] != 'AppMagic' or appmagic['country'] != 'worldwide' or appmagic['store'] != 'all':
        raise ValueError('AppMagic 月度范围口径未核实')
    appmagic_rows = {row['appId']: row for row in appmagic['rows']}
    if len(appmagic_rows) != len(appmagic['rows']) or any(row['month'] != appmagic['month'] for row in appmagic_rows.values()):
        raise ValueError('AppMagic 包含重复 App ID 或不一致月份')
    appmagic['coverage'] = sum(app['id'] in appmagic_rows for app in result['apps'])
    for metric in ('downloads', 'revenue'):
        appmagic[metric + 'Coverage'] = sum(metric in appmagic_rows.get(app['id'], {}) for app in result['apps'])
    result['appmagicMetrics'] = appmagic
    appmagic_us = json.loads((ROOT / 'data/appmagic-us-public-snapshot.json').read_text())
    if appmagic_us['country'] != 'us' or appmagic_us['periodLabel'] != '最近30天':
        raise ValueError('AppMagic 美国推算口径未核实')
    us_rows = {row['appId']: row for row in appmagic_us['rows']}
    if len(us_rows) != len(appmagic_us['rows']):
        raise ValueError('AppMagic 美国推算包含重复 App ID')
    appmagic_us['coverage'] = sum(app['id'] in us_rows for app in result['apps'])
    for metric in ('downloads', 'revenue'):
        appmagic_us[metric + 'Coverage'] = sum(metric in us_rows.get(app['id'], {}) for app in result['apps'])
    result['appmagicUSMetrics'] = appmagic_us
    for app in result['apps']:
        app['sensorTowerEstimate'] = sensor_rows.get(app['id'])
        app['appfiguresEstimate'] = appfigures_rows.get(app['id'])
        app['qimaiEstimate'] = qimai_rows.get(app['id'])
        app['appmagicEstimate'] = appmagic_rows.get(app['id'])
        app['appmagicUSEstimate'] = us_rows.get(app['id'])
        app['monthlyAverage'] = average_monthly(app['publicEstimate'], app['sensorTowerEstimate'], app['appfiguresEstimate'])
        app['usEstimates'], app['usMonthlyAverage'] = estimate_us_monthly(app['publicEstimate'], app['sensorTowerEstimate'], app['appfiguresEstimate'], app['appmagicUSEstimate'])


def average_monthly(iosmrr, sensor, appfigures=None):
    """Arithmetic mean of numeric point estimates; censored ranges stay excluded."""
    def sensor_value(text):
        match = re.fullmatch(r'\$?(\d+(?:\.\d+)?)([KM]?)', (text or '').replace(',', '').replace(' ', ''), re.I)
        return None if match is None else float(match[1]) * {'': 1, 'K': 1000, 'M': 1000000}[match[2].upper()]

    result = {}
    for output, ios_key, sensor_key in [('downloads', 'downloadsMonthly', 'downloads'), ('revenueUSD', 'estimatedMRRUSD', 'revenue')]:
        af_key, bound_key = ('downloadsMonthly', 'downloadsBound') if output == 'downloads' else ('revenueMonthlyUSD', 'revenueBound')
        af_value = (appfigures or {}).get(af_key) if not (appfigures or {}).get(bound_key) else None
        values = [value for value in [(iosmrr or {}).get(ios_key), sensor_value((sensor or {}).get(sensor_key)), af_value] if value is not None]
        result[output] = sum(values) / len(values) if values else None
        result[output + 'Sources'] = len(values)
    return result


def estimate_us_monthly(iosmrr, sensor, appfigures, appmagic):
    """Prefer US estimates; otherwise average available original global totals."""
    estimates = {source: {} for source in ('IOSMRR', 'Sensor Tower', 'Appfigures', 'AppMagic')}
    average = {}
    for key, output in [('downloads', 'downloads'), ('revenue', 'revenueUSD')]:
        share = (appmagic or {}).get(key) or {}
        use_us = share.get('shareBasis', 'us') == 'us' and share.get('usPercent') is not None
        percent = share['usPercent'] if use_us else 100
        if not 0 < percent <= 100:
            raise ValueError('AppMagic 美国占比超出范围')
        basis = 'us' if use_us else 'global'
        provenance = {'usPercent': percent if use_us else None, 'shareBasis': basis, 'sharePercent': percent if use_us else None}
        ios_key = 'downloadsMonthly' if key == 'downloads' else 'estimatedMRRUSD'
        af_key, bound_key = ('downloadsMonthly', 'downloadsBound') if key == 'downloads' else ('revenueMonthlyUSD', 'revenueBound')
        sensor_match = re.fullmatch(r'([<>]?)\$?(\d+(?:\.\d+)?)([KMB]?)', ((sensor or {}).get(key) or '').replace(',', '').replace(' ', ''), re.I)
        sensor_number = None if sensor_match is None else float(sensor_match[2]) * {'': 1, 'K': 1000, 'M': 1000000, 'B': 1000000000}[sensor_match[3].upper()]
        magic_global = (appmagic or {}).get('globalTotals', {}).get(key) or {}
        values = [
            ('IOSMRR', (iosmrr or {}).get(ios_key), ''),
            ('Sensor Tower', sensor_number, sensor_match[1] if sensor_match else ''),
            ('Appfigures', (appfigures or {}).get(af_key), {'upper_bound': '≤', 'lower_bound': '≥'}.get((appfigures or {}).get(bound_key), '')),
            ('AppMagic', magic_global.get('threshold', share.get('globalThreshold')), magic_global.get('operator', share.get('operator', ''))),
        ]
        for source, value, operator in values:
            if value is not None:
                estimates[source][key] = {'value': value * percent / 100, 'rawValue': value, 'operator': operator, **provenance}
        numbers = [row[key]['value'] for row in estimates.values() if key in row]
        average[output] = sum(numbers) / len(numbers) if numbers else None
        average[output + 'Sources'] = len(numbers)
        average[output + 'ShareBasis'] = basis if numbers else None
    return estimates, average


if __name__ == '__main__':
    result = fetch_rank()
    print(f"Fetched {len(result['apps'])} US Utilities Top Grossing apps at {result['capturedAt']}")
