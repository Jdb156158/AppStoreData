import unittest
from scripts.us_utilities import estimate_us_monthly


class USProviderAverageTests(unittest.TestCase):
    def setUp(self):
        self.magic = {
            'downloads': {'threshold': 850000, 'globalThreshold': 5000000, 'usPercent': 17, 'operator': '>'},
            'revenue': {'threshold': 5200000, 'globalThreshold': 10000000, 'usPercent': 52, 'operator': '>'},
        }

    def test_four_providers_are_scaled_before_average_and_magic_not_scaled_twice(self):
        sources, average = estimate_us_monthly(
            {'downloadsMonthly': 2000000, 'estimatedMRRUSD': 11000000},
            {'downloads': '2M', 'revenue': '$11M'},
            {'downloadsMonthly': 6000000, 'revenueMonthlyUSD': 15000000}, self.magic)
        self.assertEqual(sources['IOSMRR']['downloads']['value'], 340000)
        self.assertEqual(sources['Appfigures']['downloads']['value'], 1020000)
        self.assertEqual(sources['AppMagic']['downloads']['value'], 850000)
        self.assertEqual(average, {'downloads': 637500, 'downloadsSources': 4, 'downloadsShareBasis': 'us', 'revenueUSD': 6110000, 'revenueUSDSources': 4, 'revenueUSDShareBasis': 'us'})

    def test_missing_us_uses_global_totals_even_when_an_old_other_proxy_exists(self):
        self.magic['downloads'] = {'threshold': 150, 'globalThreshold': 5000, 'usPercent': None, 'shareBasis': 'other_regions', 'sharePercent': 3, 'operator': '>'}
        sources, average = estimate_us_monthly({'downloadsMonthly': 10000}, {'downloads': '20K'}, None, self.magic)
        self.assertEqual(sources['IOSMRR']['downloads']['value'], 10000)
        self.assertEqual(sources['Sensor Tower']['downloads']['value'], 20000)
        self.assertEqual(sources['AppMagic']['downloads']['value'], 5000)
        self.assertEqual(average['downloads'], 35000/3)
        self.assertEqual(average['downloadsSources'], 3)
        self.assertEqual(average['downloadsShareBasis'], 'global')
        self.assertTrue(all(v['downloads']['usPercent'] is None for v in sources.values() if 'downloads' in v))
        self.assertEqual(average['revenueUSDShareBasis'], 'us')

    def test_range_thresholds_are_used_as_numbers_and_missing_not_zero(self):
        sources, average = estimate_us_monthly(None, {'downloads': '<5K'}, {'downloadsMonthly': 5000, 'downloadsBound': 'upper_bound'}, self.magic)
        self.assertEqual(sources['Sensor Tower']['downloads']['operator'], '<')
        self.assertEqual(sources['Appfigures']['downloads']['operator'], '≤')
        self.assertEqual(sources['Sensor Tower']['downloads']['value'], 850)
        self.assertEqual(average['downloads'], (850+850+850000)/3)
        self.assertEqual(average['downloadsSources'], 3)
        self.assertEqual(average['revenueUSD'], 5200000)
        self.assertEqual(average['revenueUSDSources'], 1)

    def test_revenue_share_cannot_fill_missing_download_share(self):
        del self.magic['downloads']
        sources, average = estimate_us_monthly({'downloadsMonthly': 2000000, 'estimatedMRRUSD': 0}, None, None, self.magic)
        self.assertEqual(average['downloads'], 2000000)
        self.assertEqual(average['downloadsSources'], 1)
        self.assertEqual(sources['IOSMRR']['downloads']['shareBasis'], 'global')
        self.assertEqual(average['revenueUSD'], 2600000)
        self.assertEqual(average['revenueUSDSources'], 2)

    def test_without_us_share_global_totals_remain_available(self):
        _, average = estimate_us_monthly({'downloadsMonthly': 2000000}, {'downloads': '2M'}, {'revenueMonthlyUSD': 1000000}, None)
        self.assertEqual(average['downloads'], 2000000)
        self.assertEqual(average['downloadsSources'], 2)
        self.assertEqual(average['revenueUSD'], 1000000)
        self.assertEqual(average['downloadsShareBasis'], 'global')

    def test_missing_global_values_are_unknown_but_real_zero_is_included(self):
        _, average = estimate_us_monthly(None, None, None, None)
        self.assertIsNone(average['downloads'])
        self.assertEqual(average['downloadsSources'], 0)
        _, average = estimate_us_monthly({'downloadsMonthly': 0}, {'downloads': '2K'}, None, None)
        self.assertEqual(average['downloads'], 1000)
        self.assertEqual(average['downloadsSources'], 2)

    def test_invalid_percent_is_rejected(self):
        self.magic['downloads']['usPercent'] = 101
        with self.assertRaises(ValueError): estimate_us_monthly(None, None, None, self.magic)
