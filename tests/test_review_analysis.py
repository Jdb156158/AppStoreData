import sys
import unittest
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from unittest.mock import patch
from review_analysis import summarize, collect_app


class ReviewAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.end = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
        self.start = self.end - timedelta(days=30)

    def entry(self, review_id, stars, when, body=''):
        return {'id': {'label': review_id}, 'im:rating': {'label': str(stars)},
                'updated': {'label': when.isoformat()}, 'content': {'label': body}}

    def test_window_stars_duplicates_and_denominator(self):
        entries = [self.entry('one', 1, self.start, 'charged charged payment'),
                   self.entry('one', 1, self.start, 'charged charged payment'),
                   self.entry('three', 3, self.end), self.entry('four', 4, self.end),
                   self.entry('five', 5, self.end), self.entry('old', 2, self.start - timedelta(seconds=1)),
                   self.entry('future', 1, self.end + timedelta(seconds=1)), self.entry('bad', 6, self.end)]
        result = summarize(entries, self.start, self.end)
        self.assertEqual(result['writtenReviewCount'], 4)
        self.assertEqual(result['negativeWrittenReviewCount'], 2)
        self.assertIsNone(result['ratings'])  # Never turn a written sample into an all-ratings percentage.
        self.assertEqual(result['themes'][0]['count'], 1)  # One count per matching review, not per keyword.
        self.assertEqual({r['stars'] for r in result['reviews']}, {1, 3})

    def test_updated_review_uses_latest_stars(self):
        result = summarize([self.entry('same', 1, self.start), self.entry('same', 5, self.end)], self.start, self.end)
        self.assertEqual(result['writtenReviewCount'], 1)
        self.assertEqual(result['negativeWrittenReviewCount'], 0)
        self.assertIsNone(result['ratings'])

    def test_page_cap_is_partial_but_all_negative_details_are_retained(self):
        page = 0
        def response(*args, **kwargs):
            nonlocal page
            page += 1
            feed = {'entry': [self.entry(str(page*100+i), 1, self.end) for i in range(50)],
                    'link': [{'attributes': {'rel': 'next'}}]}
            return io.BytesIO(json.dumps({'feed': feed}).encode())
        with patch('review_analysis.urlopen', side_effect=response):
            result = collect_app('1234', self.start, self.end)
        self.assertEqual(result['pagesFetched'], 10)
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(result['windowCovered'])
        self.assertEqual(result['negativeWrittenReviewCount'], 500)
        self.assertEqual(len(result['reviews']), 500)
        self.assertEqual(len({r['id'] for r in result['reviews']}), 500)

    def test_endpoint_failure_is_unknown_not_zero_ratings(self):
        with patch('review_analysis.urlopen', side_effect=OSError('service unavailable')):
            result = collect_app('1234', self.start, self.end)
        self.assertEqual(result['status'], 'unavailable')
        self.assertFalse(result['windowCovered'])
        self.assertIsNone(result['ratings'])


if __name__ == '__main__':
    unittest.main()
