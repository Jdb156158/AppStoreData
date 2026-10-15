import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from star_ratings import parse_ratings


class StarRatingsTests(unittest.TestCase):
    def html(self, total=100, stars=(5, 10, 15, 20, 50)):
        return '<span class="rating-count">' + str(total) + ' Ratings</span>' + ''.join(
            f'<div class="vote" role="text" aria-label="{star} stars, {count} ratings"></div>'
            for star, count in reversed(list(enumerate(stars, 1))))

    def test_all_star_counts_are_used_instead_of_written_reviews(self):
        result = parse_ratings(self.html())
        self.assertEqual(result['byStar'], [5, 10, 15, 20, 50])
        self.assertEqual(result['total'], 100)
        self.assertEqual(result['negative'], 30)

    def test_incomplete_histogram_and_inconsistent_totals_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_ratings(self.html(total=99))
        with self.assertRaises(ValueError):
            parse_ratings('<span class="rating-count">100 Ratings</span>')

    def test_commas_and_empty_rating_populations(self):
        self.assertEqual(parse_ratings(self.html(1000, (1000, 0, 0, 0, 0)).replace('1000', '1,000'))['total'], 1000)
        self.assertEqual(parse_ratings(self.html(0, (0, 0, 0, 0, 0)))['total'], 0)


if __name__ == '__main__':
    unittest.main()
