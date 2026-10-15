"""Build the first dashboard from captured visible text and Apple's lookup response."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_page(page):
    text = page['text']
    ratings = {}
    for label, key in [('当前版本评分', 'current'), ('所有版本评分', 'all')]:
        match = re.search(label + r'\s+([\d.]+)\s+[\d.]+\s+(\d+)个评分\s+5\s+(\d+)\s+4\s+(\d+)\s+3\s+(\d+)\s+2\s+(\d+)\s+1\s+(\d+)', text)
        if match:
            ratings[key] = {'label': label, 'average': float(match[1]), 'count': int(match[2]), 'stars': [int(match[i]) for i in range(3, 8)]}
    purchases_text = text.split('热门内购\n', 1)[1].split('版本记录\n', 1)[0]
    purchases = [{'name': name.strip(), 'price': price} for name, price in re.findall(r'([^\n]+)\n(¥[\d.]+)', purchases_text)]
    versions_text = text.split('近一年版本更新', 1)[1].split('当前位置:', 1)[0]
    versions = [{'version': v, 'date': date, 'changes': int(changes)} for v, date, changes in re.findall(r'([\d]+\.[\d]+\.[\d]+\.[\d]+)\s+(?:当前\s+)?(\d{4}-\d{2}-\d{2})\s+(\d+)\s+处更改', versions_text)]
    rank = re.search(r'分类榜\s+#(\d+)\s+([^\n]+)', text)
    app_index = re.search(r'(\d+)\s+App指数', text)
    overview = text.split('全球速览\n', 1)[1].split('相似应用\n', 1)[0]
    download = re.search(r'下载量\s+([^\n]+)\s+([\d.]+)%', overview)
    income = re.search(r'收入\s+([^\n]+)\s+([\d.]+)%', overview)
    return {
        'source': page['source'], 'capturedAt': page['capturedAt'], 'method': page['method'],
        'subtitle': re.search(r'(S\d+赛季[^\n]+)', text)[1],
        'rank': {'value': int(rank[1]), 'category': rank[2], 'label': '页面分类榜'},
        'appIndex': int(app_index[1]), 'ratings': ratings, 'purchases': purchases, 'versions': versions,
        'overview': {
            'scope': '全球 · 王者荣耀合集', 'period': '最近30天',
            'download': {'display': download[1], 'changePercent': -float(download[2]), 'chinaShare': 84},
            'income': {'display': income[1], 'changePercent': float(income[2]), 'chinaShare': 98},
            'note': '来源页面选中“合集”和“最近30天”。数值为页面展示区间；非单个 iOS 应用的精确下载与收入。涨跌方向已核对页面截图。'
        },
        'registration': '粤B2-20090059-1919A', 'gameLicense': '新广出审[2017]6712号',
        'unavailable': ['精确下载量与收入', '榜单趋势时间序列', '评分及评论历史趋势', '会员功能标签']
    }


if __name__ == '__main__':
    page = json.loads((ROOT / 'data/diandian-page.json').read_text())
    apple = json.loads((ROOT / 'data/apple-lookup.json').read_text())
    apple_time = datetime.fromtimestamp((ROOT / 'data/apple-lookup.json').stat().st_mtime, timezone.utc).isoformat()
    snapshot = {'diandian': parse_page(page), 'apple': apple['results'][0], 'appleSource': 'https://itunes.apple.com/lookup?id=989673964&country=cn', 'appleCapturedAt': apple_time}
    (ROOT / 'data/snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"Built snapshot: {len(snapshot['diandian']['versions'])} versions, {len(snapshot['diandian']['purchases'])} purchases")
