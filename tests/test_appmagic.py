import copy
import json
import unittest
from pathlib import Path
from scripts.normalize_appmagic import normalize_charts
from scripts.us_utilities import normalize, attach_public_estimates, average_monthly

ROOT = Path(__file__).resolve().parents[1]


class AppMagicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads((ROOT / 'data/appmagic-monthly-public-chart-rows.json').read_text())

    def test_visible_ranges_preserve_exact_ids_thresholds_and_scope(self):
        result = normalize_charts(self.raw)
        cleanup = next(row for row in result['rows'] if row['appId'] == '1510944943')
        self.assertEqual(cleanup['downloads']['threshold'], 5000000)
        self.assertEqual(cleanup['downloads']['operator'], '>')
        self.assertEqual(cleanup['revenue']['threshold'], 10000000)
        self.assertEqual(cleanup['month'], '2026-09')
        self.assertEqual(result['store'], 'all')
        self.assertEqual(result['country'], 'worldwide')
        self.assertEqual(len(result['rows']), len({row['appId'] for row in result['rows']}))

    def test_google_play_names_cannot_be_joined_to_apple_ids(self):
        raw = copy.deepcopy(self.raw)
        raw['batches'] = [raw['batches'][0]]
        raw['batches'][0]['rows'] = [{'name': 'Cleanup', 'href': '/google-play/cleanup/com.example.cleanup', 'value': '> 5,000,000'}]
        self.assertEqual(normalize_charts(raw)['rows'], [])

    def test_wrong_month_country_and_currency_are_rejected(self):
        for suffix in ('&country=US', '&store=4', '&date=2026-08-01'):
            raw = copy.deepcopy(self.raw)
            raw['batches'][0]['sourceUrl'] += suffix
            with self.assertRaises(ValueError): normalize_charts(raw)
        raw = copy.deepcopy(self.raw)
        apple_row = next(row for row in raw['batches'][1]['rows'] if row['href'].startswith('/iphone/'))
        apple_row['value'] = '> 10,000,000'
        with self.assertRaises(ValueError): normalize_charts(raw)

    def test_conflicting_ranges_are_rejected(self):
        raw = copy.deepcopy(self.raw)
        batch = copy.deepcopy(raw['batches'][0])
        apple_row = next(row for row in batch['rows'] if row['href'].startswith('/iphone/'))
        apple_row['value'] = '> 1'
        raw['batches'].append(batch)
        with self.assertRaises(ValueError): normalize_charts(raw)

    def test_monthly_ranges_join_by_id_without_changing_point_means(self):
        chart = json.loads((ROOT / 'data/apple-us-utilities-chart-raw.json').read_text())
        result = normalize(chart)
        result['apps'].reverse()
        attach_public_estimates(result)
        cleanup = next(row for row in result['apps'] if row['id'] == '1510944943')
        self.assertEqual(cleanup['appmagicEstimate']['revenue']['operator'], '>')
        self.assertEqual(cleanup['monthlyAverage'], average_monthly(cleanup['publicEstimate'], cleanup['sensorTowerEstimate'], cleanup['appfiguresEstimate']))
        self.assertIsNone(cleanup['revenueLastMonthUSD'])
        for metric in ('downloads', 'revenue'):
            self.assertEqual(result['appmagicMetrics'][metric + 'Coverage'], sum(metric in (app['appmagicEstimate'] or {}) for app in result['apps']))
        result['apps'][0]['id'] = 'unknown-app'
        attach_public_estimates(result)
        self.assertIsNone(result['apps'][0]['appmagicEstimate'])
