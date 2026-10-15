"""Prefer US shares and retain original global totals as the fallback."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize_us(snapshot):
    if snapshot['source'] != 'AppMagic' or snapshot['country'] != 'us' or snapshot['periodLabel'] != '最近30天':
        raise ValueError('AppMagic 美国或近期口径不符')
    rows = []
    seen = set()
    for item in snapshot['rows']:
        app_id = item['appId']
        if app_id in seen or not re.fullmatch(r'https://appmagic\.rocks/(iphone|ipad)/[^/]+/' + re.escape(app_id), item['url']):
            raise ValueError('重复或不一致的 Apple ID')
        seen.add(app_id)
        links = item['visible']['appleStoreLinks']
        if not any(re.search(r'/id' + re.escape(app_id) + r'(?:\?|$)', link) for link in links):
            raise ValueError('应用商店 ID 未核实')
        row = {'appId': app_id, 'name': item['name'], 'sourceUrl': item['url'], 'capturedAt': item['capturedAt'], 'periodLabel': '最近30天', 'appCountLabel': item['visible']['appCountLabel'], 'globalTotals': {}}
        for widget in item['visible']['widgets']:
            key = 'downloads' if widget['label'].startswith('下载量:') else 'revenue' if widget['label'].startswith('收入额:') else None
            if key is None or widget['period'] != '最近30天':
                continue
            if widget['total'] == '—':
                continue
            total = re.fullmatch(r'([<>])\s*(\$?)([\d,]+)', widget['total'])
            if not total or bool(total[2]) != (key == 'revenue'):
                raise ValueError('全球范围或金额单位未核实')
            threshold = int(total[3].replace(',', ''))
            row['globalTotals'][key] = {'operator': total[1], 'threshold': threshold, 'raw': widget['total']}
            share = re.fullmatch(r'(\d+)%\s*(?:美国|United States)', widget.get('usShare', ''))
            basis = 'us' if share is not None and int(share[1]) > 0 else 'global'
            percent = int(share[1]) if basis == 'us' else 100
            if percent > 100:
                raise ValueError('占比或金额单位未核实')
            row[key] = {'operator': total[1], 'threshold': threshold * percent / 100, 'usPercent': percent if basis == 'us' else None,
                        'shareBasis': basis, 'sharePercent': percent if basis == 'us' else None, 'globalThreshold': threshold, 'rawGlobalTotal': widget['total'], 'approximate': True}
        if 'downloads' in row or 'revenue' in row:
            rows.append(row)
    return {
        'source': 'AppMagic', 'country': 'us', 'store': 'app_collection', 'periodLabel': '最近30天', 'month': None,
        'capturedAt': snapshot['capturedAt'], 'currency': 'USD', 'rows': rows,
        'note': '同一指标有美国占比时使用美国推算，否则使用全球原始总量并计入参考均值。每项注明美国或全球口径，下载、收入分别选择。占比为整数百分比，存在舍入；范围阈值按显示数值计入均值，不代表精确值或严格上下限。最近30天起止日期未披露，不等同于上个自然月。应用合并商店，未拆分 iOS；收入为扣平台和税费后的预计内购收入。总量也缺失时保留未知，不填零。',
    }


if __name__ == '__main__':
    snapshot = json.loads((ROOT / 'data/appmagic-us-share-raw.json').read_text())
    result = normalize_us(snapshot)
    (ROOT / 'data/appmagic-us-public-snapshot.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Normalized {len(result['rows'])} US recent-30-day estimates")
