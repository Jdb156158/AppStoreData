import copy
import json
import unittest
from datetime import date
from pathlib import Path
from scripts.us_utilities import normalize, attach_public_estimates, average_monthly


class RankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads((Path(__file__).resolve().parents[1] / 'data/apple-us-utilities-chart-raw.json').read_text())
        snapshot = json.loads((Path(__file__).resolve().parents[1] / 'data/iosmrr-public-snapshot.json').read_text())
        cls.iosmrr_ids = {row['appId'] for row in snapshot['rows']}
        cls.feed_ids = set(cls.raw['pageData']['segmentedControl']['segments'][0]['pageData']['selectedChart']['adamIds'])

    def test_real_feed_keeps_order_and_ids(self):
        result = normalize(self.raw)
        expected = self.raw['pageData']['segmentedControl']['segments'][0]['pageData']['selectedChart']['adamIds']
        self.assertEqual([app['id'] for app in result['apps']], expected)
        self.assertEqual([app['rank'] for app in result['apps']], list(range(1,201)))

    def test_free_chart_cannot_be_mislabeled_as_grossing(self):
        raw = copy.deepcopy(self.raw)
        raw['pageData']['segmentedControl']['segments'][0]['pageData']['selectedChart']['id'] = '27'
        with self.assertRaises(ValueError): normalize(raw)

    def test_wrong_country_is_rejected(self):
        raw = copy.deepcopy(self.raw)
        raw['pageData']['segmentedControl']['segments'][0]['pageData']['metricsBase']['storeFrontHeader'] = '143465,29'
        with self.assertRaises(ValueError): normalize(raw)

    def test_wrong_category_is_rejected(self):
        raw = copy.deepcopy(self.raw)
        raw['pageData']['segmentedControl']['segments'][0]['pageData']['genre']['id'] = '6007'
        with self.assertRaises(ValueError): normalize(raw)

    def test_incomplete_ranking_is_rejected(self):
        raw = copy.deepcopy(self.raw)
        raw['pageData']['segmentedControl']['segments'][0]['pageData']['selectedChart']['adamIds'].pop()
        with self.assertRaises(ValueError): normalize(raw)

    def test_duplicate_app_is_rejected(self):
        raw = copy.deepcopy(self.raw)
        ids = raw['pageData']['segmentedControl']['segments'][0]['pageData']['selectedChart']['adamIds']
        ids[1] = ids[0]
        with self.assertRaises(ValueError): normalize(raw)

    def test_initial_release_does_not_use_latest_version_date(self):
        app_id = int(self.raw['pageData']['segmentedControl']['segments'][0]['pageData']['selectedChart']['adamIds'][0])
        metadata = {'results': [{'trackId': app_id, 'releaseDate': '2020-12-05T08:00:00Z', 'currentVersionReleaseDate': '2026-10-12T08:02:07Z'}]}
        app = normalize(self.raw, metadata)['apps'][0]
        self.assertEqual(app['releasedAt'], '2020-12-05T08:00:00Z')
        self.assertNotEqual(app['releasedAt'], app['updatedAt'])

    def test_initial_release_survives_lookup_unavailability(self):
        result = normalize(self.raw)
        first = result['apps'][0]
        self.assertEqual(first['releasedAt'], self.raw['storePlatformData']['lockup']['results'][first['id']]['releaseDate'])

    def test_last_month_uses_calendar_month_and_handles_year_boundary(self):
        self.assertEqual(normalize(self.raw, as_of=date(2026,10,12))['commercialMetrics']['month'], '2026-09')
        self.assertEqual(normalize(self.raw, as_of=date(2026,1,1))['commercialMetrics']['month'], '2025-12')

    def test_unavailable_commercial_metrics_are_null_not_zero(self):
        app = normalize(self.raw)['apps'][0]
        for key in ['downloadsLifetime','downloadsLastMonth','revenueLifetimeUSD','revenueLastMonthUSD']:
            self.assertIsNone(app[key])

    def test_public_estimates_join_by_app_id_without_overwriting_us_metrics(self):
        result = normalize(self.raw)
        result['apps'].reverse()
        attach_public_estimates(result)
        app = next(app for app in result['apps'] if app['id'] == '1510944943')
        self.assertEqual(app['publicEstimate']['downloadsMonthly'], 2000000)
        self.assertEqual(app['publicEstimate']['estimatedMRRUSD'], 11000000)
        self.assertIsNone(app['downloadsLastMonth'])
        self.assertIsNone(app['revenueLastMonthUSD'])
        self.assertIsNone(result['publicMetrics']['country'])
        self.assertEqual(result['publicMetrics']['coverage'], len(self.iosmrr_ids & self.feed_ids))
        self.assertEqual(result['publicMetrics']['month'], '2026-09')

    def test_new_ranking_app_does_not_inherit_another_apps_estimate(self):
        result = normalize(self.raw)
        result['apps'][0]['id'] = 'unknown-app'
        attach_public_estimates(result)
        self.assertIsNone(result['apps'][0]['publicEstimate'])
        replaced_id = self.raw['pageData']['segmentedControl']['segments'][0]['pageData']['selectedChart']['adamIds'][0]
        self.assertEqual(result['publicMetrics']['coverage'], len(self.iosmrr_ids & (self.feed_ids - {replaced_id})))

    def test_monthly_mean_of_two_providers(self):
        result = average_monthly({'downloadsMonthly': 20000, 'estimatedMRRUSD': 1000000}, {'downloads': '30K', 'revenue': '$900K'})
        self.assertEqual(result, {'downloads': 25000, 'downloadsSources': 2, 'revenueUSD': 950000, 'revenueUSDSources': 2})

    def test_qimai_daily_join_does_not_change_monthly_means(self):
        result = normalize(self.raw)
        result['apps'].reverse()
        attach_public_estimates(result)
        app = next(a for a in result['apps'] if a['id'] == '1510944943')
        self.assertEqual(app['qimaiEstimate']['downloadsEstimate'], 23742)
        self.assertEqual(app['qimaiEstimate']['country'], 'us')
        self.assertEqual(app['qimaiEstimate']['periodLabel'], '昨日')
        self.assertIsNone(app['qimaiEstimate']['absoluteMetricDate'])
        self.assertEqual(app['monthlyAverage'], average_monthly(app['publicEstimate'], app['sensorTowerEstimate'], app['appfiguresEstimate']))
        result['apps'][0]['id'] = 'unknown-app'
        attach_public_estimates(result)
        self.assertIsNone(result['apps'][0]['qimaiEstimate'])

    def test_censored_download_is_not_treated_as_5000(self):
        result = average_monthly({'downloadsMonthly': 1000, 'estimatedMRRUSD': 3000000}, {'downloads': '<5K', 'revenue': '$3M'})
        self.assertEqual(result['downloads'], 1000)
        self.assertEqual(result['downloadsSources'], 1)
        self.assertEqual(result['revenueUSDSources'], 2)

    def test_missing_estimates_do_not_dilute_mean_and_zero_remains_valid(self):
        self.assertIsNone(average_monthly(None, None)['downloads'])
        result = average_monthly({'downloadsMonthly': 0, 'estimatedMRRUSD': 0}, None)
        self.assertEqual(result['downloads'], 0)
        self.assertEqual(result['downloadsSources'], 1)

    def test_monthly_mean_includes_appfigures_and_excludes_its_bounds(self):
        ios = {'downloadsMonthly': 20000, 'estimatedMRRUSD': 1000000}
        sensor = {'downloads': '30K', 'revenue': '$900K'}
        af = {'downloadsMonthly': 25000, 'revenueMonthlyUSD': 1100000}
        result = average_monthly(ios, sensor, af)
        self.assertEqual(result['downloads'], 25000)
        self.assertEqual(result['downloadsSources'], 3)
        self.assertEqual(result['revenueUSD'], 1000000)
        af['downloadsBound'] = 'upper_bound'
        af['revenueBound'] = 'lower_bound'
        result = average_monthly(ios, sensor, af)
        self.assertEqual(result['downloadsSources'], 2)
        self.assertEqual(result['revenueUSD'], 950000)
        self.assertEqual(average_monthly(None, None, {'revenueMonthlyUSD': 0})['revenueUSD'], 0)

    def test_appfigures_exact_id_join_preserves_us_fields(self):
        result = normalize(self.raw)
        result['apps'].reverse()
        attach_public_estimates(result)
        app = next(a for a in result['apps'] if a['id'] == '1194582243')
        self.assertEqual(app['appfiguresEstimate']['downloadsMonthly'], 80000)
        self.assertEqual(app['appfiguresEstimate']['revenueMonthlyUSD'], 1000000)
        self.assertEqual(app['appfiguresEstimate']['month'], '2026-09')
        self.assertIsNone(app['revenueLastMonthUSD'])
        result['apps'][0]['id'] = 'unknown-app'
        attach_public_estimates(result)
        self.assertIsNone(result['apps'][0]['appfiguresEstimate'])
