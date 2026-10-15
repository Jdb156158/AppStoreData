"""Add cached English-to-Chinese machine translations without changing review originals."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import ctranslate2
import langid
import sentencepiece

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / '.local/translation-model/opus-mt-en-zh'
CACHE = ROOT / '.local/review-translations.json'
MODEL_ID = 'Helsinki-NLP/opus-mt-en-zh:ct2-8ed73397'


def enrich(snapshot):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    source = sentencepiece.SentencePieceProcessor(model_file=str(MODEL / 'source.spm'))
    target = sentencepiece.SentencePieceProcessor(model_file=str(MODEL / 'target.spm'))
    translator = ctranslate2.Translator(str(MODEL), device='cpu', compute_type='int8', intra_threads=4)
    pending = {}
    for app in snapshot['apps'].values():
        for review in app['reviews']:
            value = review['body']
            key = hashlib.sha256((MODEL_ID + '\0' + value).encode()).hexdigest()
            if not value or key in cache:
                continue
            text = re.sub(r'[^\w\s]', ' ', value).lower()
            if langid.classify(text)[0] != 'en':
                continue
            pending[key] = value
    # Bound input segments so long reviews are translated in full rather than silently truncated.
    segments, owners = [], []
    for key, value in pending.items():
        for paragraph in value.splitlines():
            for sentence in re.split(r'(?<=[.!?])\s+', paragraph):
                tokens = source.encode(sentence, out_type=str)
                for start in range(0, len(tokens), 180):
                    segments.append(['>>cmn_Hans<<'] + tokens[start:start+180] + ['</s>'])
                    owners.append(key)
        cache[key] = ''
    print(f'Translating {len(pending)} new text fields ({len(segments)} segments)', file=sys.stderr, flush=True)
    for start in range(0, len(segments), 32):
        results = translator.translate_batch(segments[start:start+32], beam_size=4, max_decoding_length=512)
        for key, tokens, result in zip(owners[start:start+32], segments[start:start+32], results):
            text = target.decode(result.hypotheses[0]).strip()
            if not text:
                text = source.decode(tokens[1:-1]).strip()
            cache[key] += ('\n' if cache[key] else '') + text
    translated = 0
    for app in snapshot['apps'].values():
        for review in app['reviews']:
            key = hashlib.sha256((MODEL_ID + '\0' + review['body']).encode()).hexdigest()
            if cache.get(key):
                text = cache[key]
                if re.search(r'\btrial\b', review['body'], re.I):
                    text = text.replace('庭审费', '试用费用').replace('庭审', '试用').replace('审判', '试用').replace('审讯', '试用')
                if re.search(r'\bstorage\b', review['body'], re.I):
                    text = text.replace('仓库', '存储空间').replace('储藏室', '存储空间')
                review['translation'] = {'language': 'zh-CN', 'provider': 'OPUS-MT', 'model': MODEL_ID,
                                         'body': text}
                translated += 1
    temporary = CACHE.with_suffix('.tmp')
    temporary.write_text(json.dumps(cache, ensure_ascii=False))
    temporary.replace(CACHE)
    return translated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/review-analysis.json')
    args = parser.parse_args()
    snapshot = json.loads(args.input.read_text())
    count = enrich(snapshot)
    temporary = args.input.with_suffix('.translation.tmp')
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False))
    temporary.replace(args.input)
    print(json.dumps({'translatedReviews': count}, ensure_ascii=False))


if __name__ == '__main__':
    main()
