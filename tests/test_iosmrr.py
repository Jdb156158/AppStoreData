import unittest
from unittest.mock import patch
from scripts.fetch_iosmrr import parse_page, fetch_app


PAGE = '''<div>DATA · SEP 2026</div><table><tr>
<td>101</td><td><a href="https://apps.apple.com/app/id1510944943"><span class="app-name">Cleanup &amp; Photos</span></a></td>
<td>Utilities</td><td>$11,000,000<div class="delta">▼ -25.0%</div></td>
<td>2,000,000</td><td>$5.50</td><td>4.7</td></tr></table>'''


class PublicIOSMRRTests(unittest.TestCase):
    def test_visible_monthly_values_do_not_include_change_or_price(self):
        row = parse_page(PAGE)[0]
        self.assertEqual(row, {'appId': '1510944943', 'name': 'Cleanup & Photos', 'downloads': '2,000,000', 'revenue': '$11,000,000'})

    def test_changed_month_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_page(PAGE.replace('SEP 2026', 'OCT 2026'))

    def test_name_similarity_cannot_replace_exact_id(self):
        with patch('scripts.fetch_iosmrr.fetch_page', return_value=parse_page(PAGE)):
            self.assertIsNone(fetch_app({'id': 'another-app', 'name': 'Cleanup & Photos'}))


if __name__ == '__main__':
    unittest.main()
