"""Local static server with one fixed, anonymous Apple ranking API."""
import json
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlparse
from urllib.error import URLError
from scripts.us_utilities import fetch_rank

ROOT = Path(__file__).resolve().parent
cache = None
cached_at = 0
lock = Lock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        global cache, cached_at
        parsed = urlparse(self.path)
        if parsed.path != '/api/us-utilities':
            return super().do_GET()
        refresh = parse_qs(parsed.query).get('refresh') == ['1']
        try:
            with lock:
                if cache is None or refresh or time.monotonic() - cached_at > 300:
                    cache = fetch_rank()
                    cached_at = time.monotonic()
                payload = json.dumps(cache, ensure_ascii=False).encode()
            status = 200
        except (URLError, TimeoutError, ValueError, KeyError) as error:
            status = 502
            payload = json.dumps({'error': f'Apple 榜单请求失败：{error}'}, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    print('AppStoreData: http://127.0.0.1:4173/us-utilities.html', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 4173), Handler).serve_forever()
