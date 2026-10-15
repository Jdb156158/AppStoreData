"""Send the existing PNG and link as one Feishu bot message, without Lark UI."""
import argparse
import json
import subprocess
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

APP_ID = 'cli_aa30a7427ef85bc1'
BASE = 'https://open.feishu.cn/open-apis'


def request_api(path, body, token=None, content_type='application/json'):
    headers = {'Content-Type': content_type}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(BASE + path, data=body, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as error:
        result = json.load(error)
    if result.get('code') != 0:
        raise RuntimeError(f"飞书 API {result.get('code')}: {result.get('msg')}")
    return result


def message_content(payload, image_key):
    return {'zh_cn': {'title': '美区工具畅销榜 · Top 10', 'content': [
        [{'tag': 'img', 'image_key': image_key}],
        [{'tag': 'text', 'text': payload['message'].replace(payload['siteUrl'], '').strip()}],
        [{'tag': 'a', 'text': '查看完整 Top 200 与数据来源', 'href': payload['siteUrl']}],
    ]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chat-id', required=True, help='Verified chat ID for 工具-产品组')
    parser.add_argument('--payload-file', required=True)
    parser.add_argument('--dry-run', action='store_true', help='Preview content without authenticating or sending')
    args = parser.parse_args()
    payload = json.loads(Path(args.payload_file).read_text())
    image = Path(payload['imagePath'])
    if image.suffix.lower() != '.png' or not image.is_file():
        raise ValueError('PNG 图片不存在')
    if args.dry_run:
        print(json.dumps({'previewOnly': True, 'receive_id': args.chat_id,
                          'msg_type': 'post', 'content': message_content(payload, 'UPLOAD_RESULT_IMAGE_KEY')}, ensure_ascii=False))
        return
    secret = subprocess.run(['/usr/bin/security', 'find-generic-password', '-a', APP_ID,
                             '-s', 'codex-feishu-mcp', '-w'], check=True, capture_output=True, text=True).stdout.strip()
    token = request_api('/auth/v3/tenant_access_token/internal',
                        json.dumps({'app_id': APP_ID, 'app_secret': secret}).encode())['tenant_access_token']
    boundary = 'FeishuChart' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image_type"\r\n\r\nmessage\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="chart.png"\r\n'
            'Content-Type: image/png\r\n\r\n').encode() + image.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    image_key = request_api('/im/v1/images', body, token, 'multipart/form-data; boundary=' + boundary)['data']['image_key']
    message = {'receive_id': args.chat_id, 'msg_type': 'post',
               'content': json.dumps(message_content(payload, image_key), ensure_ascii=False)}
    result = request_api('/im/v1/messages?receive_id_type=chat_id', json.dumps(message, ensure_ascii=False).encode(), token)
    message_id = result.get('data', {}).get('message_id')
    if not message_id:
        raise RuntimeError('飞书未返回消息 ID，不能确认发送成功')
    if result['data'].get('chat_id') != args.chat_id:
        raise RuntimeError('飞书返回的目标群与配置不符，停止后续发送')
    print(json.dumps({'messageId': message_id, 'chatId': args.chat_id,
                      'capturedAt': payload['capturedAt']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
