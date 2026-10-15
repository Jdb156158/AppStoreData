import copy
import unittest
from scripts.normalize_appmagic_us import normalize_us
import json
from pathlib import Path
from scripts.us_utilities import normalize, attach_public_estimates


class USShareTests(unittest.TestCase):
    def setUp(self):
        self.raw = {'source': 'AppMagic', 'country': 'us', 'periodLabel': '最近30天', 'capturedAt': '2026-10-14T02:00:00Z', 'rows': [{
            'appId': '1510944943', 'name': 'Cleanup', 'url': 'https://appmagic.rocks/iphone/cleanup/1510944943', 'capturedAt': '2026-10-14T02:00:00Z',
            'visible': {'appCountLabel': '3个 应用分析数据', 'appleStoreLinks': ['https://apps.apple.com/us/app/cleanup/id1510944943'], 'widgets': [
                {'label': '下载量: > 5,000,000', 'total': '> 5,000,000', 'period': '最近30天', 'usShare': '17% 美国'},
                {'label': '收入额: > $10,000,000', 'total': '> $10,000,000', 'period': '最近30天', 'usShare': '52% 美国'},
            ]}}]}

    def test_download_and_revenue_use_their_own_us_share(self):
        data = normalize_us(self.raw)
        row = data['rows'][0]
        self.assertEqual(row['downloads']['threshold'], 850000)
        self.assertEqual(row['revenue']['threshold'], 5200000)
        self.assertEqual(row['revenue']['operator'], '>')
        self.assertTrue(row['revenue']['approximate'])
        self.assertIsNone(data['month'])
        self.assertEqual(data['country'], 'us')

    def test_missing_us_download_share_is_not_replaced_by_revenue_share(self):
        del self.raw['rows'][0]['visible']['widgets'][0]['usShare']
        row = normalize_us(self.raw)['rows'][0]
        self.assertEqual(row['downloads']['threshold'], 5000000)
        self.assertEqual(row['downloads']['shareBasis'], 'global')
        self.assertIn('revenue', row)
        self.assertEqual(row['globalTotals']['downloads']['threshold'], 5000000)
        self.assertEqual(row['globalTotals']['downloads']['operator'], '>')

    def test_us_is_preferred_and_global_is_used_when_missing_regardless_of_other_share(self):
        widgets = self.raw['rows'][0]['visible']['widgets']
        widgets[0]['otherShare'] = '3% 其他地区'
        self.assertEqual(normalize_us(self.raw)['rows'][0]['downloads']['usPercent'], 17)
        del widgets[0]['usShare']
        value = normalize_us(self.raw)['rows'][0]['downloads']
        self.assertEqual(value['threshold'], 5000000)
        self.assertIsNone(value['usPercent'])
        self.assertEqual(value['shareBasis'], 'global')
        self.assertIsNone(value['sharePercent'])
        widgets[0].pop('otherShare')
        widgets[1]['otherShare'] = '7% 其他地区'
        self.assertEqual(normalize_us(self.raw)['rows'][0]['downloads']['threshold'], 5000000)

    def test_lifetime_share_cannot_scale_a_monthly_total(self):
        self.raw['rows'][0]['visible']['widgets'][0]['period'] = '上线至今'
        self.assertNotIn('downloads', normalize_us(self.raw)['rows'][0])

    def test_unavailable_global_total_is_not_zero(self):
        widget = self.raw['rows'][0]['visible']['widgets'][0]
        widget['total'] = '—'
        del widget['usShare']
        row = normalize_us(self.raw)['rows'][0]
        self.assertNotIn('downloads', row['globalTotals'])
        self.assertNotIn('downloads', row)

    def test_upper_bound_is_preserved_and_zero_percent_is_unknown(self):
        widgets = self.raw['rows'][0]['visible']['widgets']
        widgets[0]['total'] = '< 1,000'
        widgets[1]['usShare'] = '0% 美国'
        row = normalize_us(self.raw)['rows'][0]
        self.assertEqual(row['downloads']['operator'], '<')
        self.assertEqual(row['downloads']['threshold'], 170)
        self.assertEqual(row['revenue']['threshold'], 10000000)
        self.assertEqual(row['revenue']['shareBasis'], 'global')

    def test_incorrect_identity_and_currency_are_rejected(self):
        for mutation in ('id', 'unit'):
            raw = copy.deepcopy(self.raw)
            if mutation == 'id': raw['rows'][0]['visible']['appleStoreLinks'] = ['https://apps.apple.com/us/app/other/id1111111111']
            else: raw['rows'][0]['visible']['widgets'][1]['total'] = '> 10,000,000'
            with self.assertRaises(ValueError): normalize_us(raw)

    def test_exact_us_join_retains_range_and_does_not_inherit_by_rank(self):
        root = Path(__file__).resolve().parents[1]
        chart = json.loads((root / 'data/apple-us-utilities-chart-raw.json').read_text())
        result = normalize(chart)
        result['apps'].reverse()
        attach_public_estimates(result)
        cleanup = next(app for app in result['apps'] if app['id'] == '1510944943')
        self.assertEqual(cleanup['appmagicUSEstimate']['revenue']['threshold'], 5200000)
        self.assertEqual(result['appmagicUSMetrics']['country'], 'us')
        self.assertIsNone(result['appmagicUSMetrics']['month'])
        result['apps'][0]['id'] = 'unknown-app'
        attach_public_estimates(result)
        self.assertIsNone(result['apps'][0]['appmagicUSEstimate'])
