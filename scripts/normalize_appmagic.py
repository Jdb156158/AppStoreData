"""Normalize visible AppMagic monthly chart ranges, matched only by Apple ID."""
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]


def normalize_charts(snapshot):
    if snapshot['source'] != 'AppMagic' or snapshot['country'] != 'worldwide' or snapshot['store'] != 'all':
        raise ValueError('AppMagic 来源、地区或商店口径不符')
    rows = {}
    for batch in snapshot['batches']:
        url = urlparse(batch['sourceUrl'])
        query = parse_qs(url.query)
        if url.netloc != 'appmagic.rocks' or query.get('date') != [snapshot['month'] + '-01'] or 'country' in query or 'store' in query:
            raise ValueError('AppMagic 月份或筛选 URL 不符')
        if batch['metric'] not in ('downloads', 'revenue'):
            raise ValueError('非下载或收入榜')
        for item in batch['rows']:
            identity = re.fullmatch(r'/(?:iphone|ipad)/[^/]+/(\d+)', item['href'])
            if not identity:
                continue  # Google Play links cannot be joined to an Apple ID by name.
            match = re.fullmatch(r'([<>])\s*(\$?)([\d,]+)', item['value'])
            if not match or bool(match[2]) != (batch['metric'] == 'revenue'):
                raise ValueError('AppMagic 公开范围或美元单位未核实')
            row = rows.setdefault(identity[1], {'appId': identity[1], 'name': item['name'], 'month': snapshot['month']})
            key = batch['metric']
            value = {'operator': match[1], 'threshold': int(match[3].replace(',', '')), 'raw': item['value'], 'sourceUrl': batch['sourceUrl'], 'appUrl': 'https://appmagic.rocks' + item['href']}
            if key in row and row[key]['raw'] != value['raw']:
                raise ValueError('同一应用的月度范围冲突')
            row[key] = value
    return {
        'source': 'AppMagic', 'sourceUrl': 'https://appmagic.rocks/top-charts/apps?date=' + snapshot['month'] + '-01&tag=115',
        'capturedAt': snapshot['capturedAt'], 'month': snapshot['month'], 'periodLabel': snapshot['periodLabel'],
        'country': 'worldwide', 'store': 'all', 'currency': 'USD',
        'revenueDefinition': snapshot['revenueDefinition'],
        'collectionMethod': '无需登录的公开月榜及工具细分类，读取网页可见范围；仅通过链接中的 Apple ID 匹配。',
        'note': '全球、全部商店的应用合并范围，不是美国 iOS 数据。仅为阈值上下限，不参与均值；未覆盖不表示零。收入为预计内购收入，已扣除平台和税费（原页提示），不包含未被该指标覆盖的收入。刷新只更新 Apple 榜单，不重新采集快照。',
        'rows': list(rows.values()),
    }


if __name__ == '__main__':
    raw = json.loads((ROOT / 'data/appmagic-monthly-public-chart-rows.json').read_text())
    result = normalize_charts(raw)
    (ROOT / 'data/appmagic-monthly-public-snapshot.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Normalized {len(result['rows'])} Apple IDs from AppMagic {result['month']} monthly ranges")
