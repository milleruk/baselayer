from datetime import date

from django.test import TestCase

from .services import compute_tier_progress


class AnnualChallengeServicesTests(TestCase):
    def test_compute_tier_progress_required_pace_matches_math(self):
        # Non-leap year
        today = date(2026, 1, 31)
        rows = compute_tier_progress(minutes_ytd=0, today=today)

        tier_2000 = next(r for r in rows if r.tier.minutes == 2000)
        self.assertAlmostEqual(tier_2000.required_min_per_day, 2000 / 365, places=6)
        self.assertAlmostEqual(tier_2000.required_min_per_week, (2000 / 365) * 7, places=6)

    def test_compute_tier_progress_needed_pace_uses_remaining_days(self):
        today = date(2026, 1, 31)  # day 31 of 365 => 334 remaining (inclusive elapsed)
        minutes_ytd = 1756
        rows = compute_tier_progress(minutes_ytd=minutes_ytd, today=today)

        tier_2000 = next(r for r in rows if r.tier.minutes == 2000)
        remaining_needed = 2000 - minutes_ytd
        remaining_days = 365 - 31
        self.assertAlmostEqual(tier_2000.needed_min_per_day, remaining_needed / remaining_days, places=6)

