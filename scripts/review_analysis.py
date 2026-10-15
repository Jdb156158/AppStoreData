"""Collect US written-review samples; these are NOT all App Store ratings."""
import argparse
import json
import re
import sys
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/review-analysis.json'
THEMES = [
    ('收费 / 试用扣款', 'charged · payment · free trial', r'\b(?:charg\w*|bill\w*|pay\w*|paid|refund\w*|free trial)\b|扣款|收费|退款|付费|试用'),
    ('订阅 / 取消续费', 'subscription · cancel · renewal', r'\b(?:subscri\w*|cancel\w*|renew\w*)\b|订阅|续费|取消'),
    ('广告干扰', 'ads · advertisement', r'\b(?:ads?|advertis\w*|commercials?)\b|广告'),
    ('功能失效', 'not working · error · broken', r"\b(?:doesn.t work|not work\w*|won.t work|does not work|error\w*|broken|fail\w*|useless)\b|不能用|无效|失效|错误"),
    ('性能 / 崩溃', 'crash · slow · freeze', r'\b(?:crash\w*|slow\w*|freez\w*|frozen|lag\w*|battery|overheat\w*)\b|卡顿|崩溃|耗电'),
    ('连接 / 网络', 'connection · network · VPN', r'\b(?:connect\w*|disconnect\w*|network|internet|vpn|offline)\b|连接|断网|网络'),
    ('隐私 / 安全', 'privacy · tracking · data', r'\b(?:privacy|track\w*|permission\w*|secur\w*|personal data|steal\w*|stolen)\b|隐私|泄露|安全'),
    ('清理 / 数据丢失', 'photos · delete · storage', r'\b(?:photos?|delet\w*|storage|duplicates?|lost|missing files)\b|照片|删除|丢失|存储'),
    ('登录 / 账号', 'login · account · password', r'\b(?:log[ -]?in|sign[ -]?in|accounts?|password\w*|verification)\b|登录|账号|密码'),
    ('客服 / 体验', 'support · confusing · difficult', r'\b(?:support|customer service|confus\w*|difficult|complicated|hard to use)\b|客服|难用|复杂'),
]


def normalize(entry, start, end):
    try:
        stars = int(entry['im:rating']['label'])
        updated = datetime.fromisoformat(entry['updated']['label'].replace('Z', '+00:00'))
        review_id = str(entry['id']['label'])
        if stars not in range(1, 6) or updated.tzinfo is None or not start <= updated <= end:
            return None
    except (KeyError, ValueError, TypeError):
        return None
    return {'id': review_id, 'stars': stars, 'updatedAt': updated.isoformat(),
            'title': entry.get('title', {}).get('label', ''),
            'body': entry.get('content', {}).get('label', ''),
            'author': entry.get('author', {}).get('name', {}).get('label', ''),
            'version': entry.get('im:version', {}).get('label', '')}


def summarize(entries, start, end):
    # A user may update a review. Keep its latest version rather than double count it.
    unique = {}
    for entry in entries:
        review = normalize(entry, start, end)
        if review and (review['id'] not in unique or datetime.fromisoformat(review['updatedAt']) > datetime.fromisoformat(unique[review['id']]['updatedAt'])):
            unique[review['id']] = review
    reviews = sorted(unique.values(), key=lambda r: datetime.fromisoformat(r['updatedAt']), reverse=True)
    negative = [review for review in reviews if review['stars'] <= 3]
    themes = []
    for label, keywords, pattern in THEMES:
        matched = [review['id'] for review in negative if re.search(pattern, review['title'] + '\n' + review['body'], re.I)]
        if matched:
            themes.append({'label': label, 'keywords': keywords, 'count': len(matched)})
    themes.sort(key=lambda theme: theme['count'], reverse=True)
    return {'writtenReviewCount': len(reviews), 'negativeWrittenReviewCount': len(negative),
            'themes': themes[:10], 'reviews': negative, 'ratings': None}


def collect_app(app_id, start, end):
    source_url = f'https://itunes.apple.com/us/rss/customerreviews/page=1/id={app_id}/sortby=mostrecent/json'
    entries, pages, complete, error = [], 0, False, None
    try:
        for page in range(1, 11):
            url = source_url.replace('page=1/', f'page={page}/')
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'X-Apple-Store-Front': '143441,12'})
            for attempt in range(2):
                try:
                    with urlopen(request, timeout=25) as response:
                        feed = json.load(response)['feed']
                    break
                except HTTPError as exc:
                    if attempt == 0 and exc.code in (403, 429, 500, 502, 503):
                        time.sleep(3)
                    else:
                        raise
            pages += 1
            batch = feed.get('entry', [])
            if isinstance(batch, dict):
                batch = [batch]
            batch = [entry for entry in batch if 'im:rating' in entry and 'updated' in entry]
            entries.extend(batch)
            dates = [datetime.fromisoformat(entry['updated']['label'].replace('Z', '+00:00')) for entry in batch]
            if dates and max(dates) < start:
                complete = True
                break
            if len(batch) < 50 or not any(link.get('attributes', {}).get('rel') == 'next' for link in feed.get('link', [])):
                complete = True
                break
    except Exception as exc:
        error = str(exc)
    summary = summarize(entries, start, end)
    return {'appId': str(app_id), 'country': 'us', 'sourceUrl': source_url,
            'capturedAt': datetime.now(timezone.utc).isoformat(), 'pagesFetched': pages,
            'status': 'partial' if not complete and pages else 'ok' if complete else 'unavailable',
            'windowCovered': complete, 'error': error, **summary}


def collect(apps):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    result = {'schemaVersion': 1, 'country': 'us', 'capturedAt': end.isoformat(),
              'window': {'startAt': start.isoformat(), 'endAt': end.isoformat()},
              'source': {'name': 'Apple 美国区 Customer Reviews RSS', 'kind': 'written_reviews', 'dateField': 'updated'},
              'ratingsNote': '公开 RSS 只有文字评论；未取得近30天全部评星及1–3星评星数，不计算全量评星差评率。',
              'apps': {}}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(collect_app, str(app['id']), start, end): app for app in apps}
        for index, future in enumerate(as_completed(futures), 1):
            app = futures[future]
            result['apps'][str(app['id'])] = future.result()
            if index % 20 == 0 or index == len(apps):
                print(f'Reviews: {index}/{len(apps)} applications collected', file=sys.stderr, flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true', help='Synchronize with the existing public Sites API')
    args = parser.parse_args()
    data = json.loads((ROOT / 'data/us-utilities.json').read_text())
    result = collect(data['apps'])
    temporary = OUTPUT.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    translator = ROOT / '.local/translation-venv/bin/python'
    if translator.exists():
        subprocess.run([str(translator), str(ROOT / 'scripts/translate_reviews.py'), '--input', str(temporary)], check=True, timeout=180, stdout=sys.stderr)
        result = json.loads(temporary.read_text())
    temporary.replace(OUTPUT)
    if args.publish:
        publish(result)
    print(json.dumps({'applications': len(result['apps']), 'writtenReviews': sum(app['writtenReviewCount'] for app in result['apps'].values()),
                      'negativeWrittenReviews': sum(app['negativeWrittenReviewCount'] for app in result['apps'].values()),
                      'unavailable': sum(app['status'] == 'unavailable' for app in result['apps'].values()), 'output': str(OUTPUT)}))


def publish(data):
    import subprocess
    token = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s', 'appstoredata-sites-updater', '-a', 'appgprj_6acf47b372a481919d1f26c06488990f', '-w'], check=True, capture_output=True, text=True).stdout.strip()
    request = Request('https://us-utilities-top-200.carlgustav.chatgpt.site/api/review-analysis', data=json.dumps(data, ensure_ascii=False).encode(), method='POST',
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    with urlopen(request, timeout=55) as response:
        receipt = json.load(response)
    if receipt.get('capturedAt') != data['capturedAt'] or receipt.get('count') != len(data['apps']):
        raise ValueError('Review synchronization receipt does not match')


if __name__ == '__main__':
    main()
