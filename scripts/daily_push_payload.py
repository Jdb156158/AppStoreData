"""Fetch Apple, synchronize the hosted chart, and prepare the Feishu summary."""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from us_utilities import fetch_rank
from render_daily_chart import render_chart

SITE_URL = 'https://us-utilities-top-200.carlgustav.chatgpt.site'


def main():
    data = fetch_rank()
    apps = data['apps']
    if data['country'] != 'us' or data['categoryId'] != '6002' or data['chart'] != 'topgrossingapplications' or len(apps) != 200 or len({app['id'] for app in apps}) != 200:
        raise ValueError('地区、榜单或应用数量不符，停止推送')
    captured = datetime.fromisoformat(data['capturedAt'].replace('Z', '+00:00'))
    if not timedelta(0) <= datetime.now(timezone.utc) - captured <= timedelta(minutes=10):
        raise ValueError('榜单不是最近10分钟获取，停止推送')
    update_token = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s', 'appstoredata-sites-updater', '-a', 'appgprj_6acf47b372a481919d1f26c06488990f', '-w'], check=True, capture_output=True, text=True).stdout.strip()
    request = Request(SITE_URL + '/api/us-utilities', data=json.dumps(data, ensure_ascii=False).encode(), method='POST', headers={'Authorization':'Bearer ' + update_token, 'Content-Type':'application/json', 'User-Agent':'Mozilla/5.0'})
    with urlopen(request, timeout=55) as response:
        receipt = json.load(response)
    if receipt['capturedAt'] != data['capturedAt'] or receipt['count'] != 200:
        raise ValueError('在线榜单同步回执不符，停止推送')
    timestamp = captured.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    message = '\n'.join([
        '美区工具畅销榜 · Top 200',
        f'榜单获取：{timestamp}（UTC+8）',
        SITE_URL,
        '',
        '前10名下载和收入见榜单图片；完整榜单与来源口径见链接。',
    ])
    print(json.dumps({'capturedAt': data['capturedAt'], 'siteUrl': SITE_URL, 'message': message, 'imagePath': render_chart(data)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
