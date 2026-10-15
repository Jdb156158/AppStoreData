"""Update the chart and send the daily PNG through Feishu's server API."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    receipts_file = ROOT / '.local/push-receipts.json'
    receipts = json.loads(receipts_file.read_text()) if receipts_file.exists() else []
    if not args.test and any(row['date'] == today and row['type'] == 'daily' for row in receipts):
        print(json.dumps({'skipped': True, 'reason': '今日已成功推送'}, ensure_ascii=False))
        return
    destination = json.loads((ROOT / '.local/feishu-destination.json').read_text())
    if destination['group'] != '工具-产品组':
        raise ValueError('目标群配置不符')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/daily_push_payload.py')],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    payload['message'] = ('[API 测试] ' if args.test else f'[日报 {today}] ') + payload['message']
    payload_file = ROOT / '.local/daily-api-payload.json'
    payload_file.write_text(json.dumps(payload, ensure_ascii=False))
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/send_feishu_api.py'),
                             '--chat-id', destination['chatId'], '--payload-file', str(payload_file)],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    receipt = json.loads(result.stdout)
    receipt.update({'date': today, 'type': 'test-api' if args.test else 'daily',
                    'group': destination['group'], 'siteUrl': payload['siteUrl'],
                    'imagePath': payload['imagePath'], 'verifiedAt': datetime.now(timezone.utc).isoformat()})
    receipts.append(receipt)
    temporary = receipts_file.with_suffix('.tmp')
    temporary.write_text(json.dumps(receipts, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(receipts_file)
    # Refresh review samples after sending, so collection cannot delay the daily message.
    if not args.test:
        try:
            subprocess.run([sys.executable, str(ROOT / 'scripts/review_analysis.py'), '--publish'],
                           cwd=ROOT, check=True, capture_output=True, text=True, timeout=300)
            receipt['reviewsUpdated'] = True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            receipt['reviewsUpdated'] = False
            receipt['reviewNote'] = '推送成功；评论更新失败，网页保留带采样日期的上次快照。'
        try:
            subprocess.run([sys.executable, str(ROOT / 'scripts/star_ratings.py'), '--publish'],
                           cwd=ROOT, check=True, capture_output=True, text=True, timeout=300)
            receipt['starRatingsUpdated'] = True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            receipt['starRatingsUpdated'] = False
            receipt['starRatingsNote'] = '推送成功；评星更新失败，网页保留带采集日期的上次快照。'
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise RuntimeError(error.stderr.strip() or f'子任务失败（{error.returncode}）') from None
