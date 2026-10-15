"""Render the reviewed Top 10 as a reproducible PNG for Feishu."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

FONT = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
ROOT = Path(__file__).resolve().parents[1]


def app_icon(app):
    url = app['icon']
    cache = ROOT / '.local' / 'app-icons' / f"{app['id']}-{sha256(url.encode()).hexdigest()[:16]}.png"
    if not cache.exists():
        with urlopen(url, timeout=15) as response:
            with Image.open(BytesIO(response.read())) as original:
                cache.parent.mkdir(parents=True, exist_ok=True)
                original.convert('RGB').save(cache)
    with Image.open(cache) as original:
        icon = original.convert('RGB').resize((64, 64), Image.Resampling.LANCZOS)
    return icon


def compact(value, currency=False):
    if value is None:
        return '未取得'
    for scale, suffix in [(1_000_000_000, 'B'), (1_000_000, 'M'), (1_000, 'K'), (1, '')]:
        if value >= scale or scale == 1:
            amount = f'{value / scale:.2f}'.rstrip('0').rstrip('.')
            return f"≈{'$' if currency else ''}{amount}{suffix}"


def render_chart(data):
    apps = data['apps'][:10]
    if len(apps) != 10 or [app['rank'] for app in apps] != list(range(1, 11)) or data['country'] != 'us':
        raise ValueError('Expected ranked US Top 10')
    captured = datetime.fromisoformat(data['capturedAt'].replace('Z', '+00:00'))
    timestamp = captured.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    image = Image.new('RGB', (1200, 1550), '#FFFFFF')
    draw = ImageDraw.Draw(image)
    fonts = {size: ImageFont.truetype(FONT, size) for size in [18, 24, 26, 28, 32, 34, 56]}
    dark, muted, blue = '#172B4D', '#61738D', '#246BCE'

    def text(x, y, value, size=32, color=dark, right=False):
        if right:
            x -= draw.textlength(value, font=fonts[size])
        draw.text((x, y), value, font=fonts[size], fill=color)

    def wrap(value, width):
        lines, line = [], ''
        for word in value.split():
            candidate = f'{line} {word}'.strip()
            if line and draw.textlength(candidate, font=fonts[32]) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
        if len(lines) > 2 or any(draw.textlength(line, font=fonts[32]) > width for line in lines):
            raise ValueError(f'App name needs a wider column: {value}')
        return lines

    draw.rectangle((48, 44, 112, 52), fill=blue)
    text(48, 68, '美区工具畅销榜', 56)
    draw.rounded_rectangle((972, 74, 1152, 134), radius=14, fill='#EAF2FF')
    text(1000, 86, 'TOP 10', 34, blue)
    text(48, 154, f'榜单获取  {timestamp}（UTC+8）', 26, muted)
    text(48, 198, '美国 · iOS · 工具 6002', 26, muted)
    draw.rounded_rectangle((48, 260, 1152, 334), radius=12, fill='#F0F4FA')
    text(70, 280, '排名', 26, muted)
    text(156, 280, '应用', 26, muted)
    text(922, 280, '近30天下载*', 26, muted, right=True)
    text(1130, 280, '近30天收入*', 26, muted, right=True)
    for index, app in enumerate(apps):
        top = 348 + index * 100
        if index % 2 == 0:
            draw.rounded_rectangle((48, top, 1152, top+96), radius=10, fill='#F8FAFD')
        text(70, top+30, f"{app['rank']:02d}", 32, blue if index < 3 else muted)
        mask = Image.new('L', (64, 64))
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 63, 63), radius=14, fill=255)
        image.paste(app_icon(app), (156, top+16), mask)
        lines = wrap(app['name'], 474)
        name_y = top + (10 if len(lines) == 2 else 30)
        for line in lines:
            text(238, name_y, line)
            name_y += 42
        average = app.get('usMonthlyAverage') or {}
        for key, currency, x in [('downloads', False, 922), ('revenueUSD', True, 1130)]:
            value = average.get(key)
            text(x, top+30, compact(value, currency), 32, muted if value is None else dark, right=True)
            if value is not None:
                text(x, top+65, '全球参考' if average.get(key+'ShareBasis') == 'global' else '美国推算', 18, muted, right=True)
    draw.line((48, 1366, 1152, 1366), fill='#DFE6EF', width=2)
    text(48, 1390, '* 美国推算优先，缺失时用全球参考；缺失不表示零。收入 USD。', 24, muted)
    text(48, 1430, '来源混合自然月、最近30天及 MRR，非统一30天统计；估算为保存的快照。', 24, muted)
    text(48, 1474, 'Apple 榜单 · 第三方估算详情与完整 Top 200 见消息中的网页链接', 24, muted)
    output = ROOT / '.local' / 'daily-charts' / f"us-utilities-{captured.strftime('%Y%m%d-%H%M%S')}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, optimize=True)
    return str(output)
