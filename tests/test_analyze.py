import pytest
from datetime import datetime
from src.analyze import find_cheapest_window, find_cheap_start_span, coverage_hours


def make_prices(values_sek, start_hour=0, date='2025-02-25'):
    """Helper: build price list from a list of SEK values, one per hour."""
    return [
        {
            'time_start': f'{date}T{(start_hour + i) % 24:02d}:00:00+01:00',
            'kWh_SEK': price,
        }
        for i, price in enumerate(values_sek)
    ]


class TestFindCheapestWindow:
    def test_returns_none_for_empty_list(self):
        assert find_cheapest_window([]) is None

    def test_returns_none_when_insufficient_data(self):
        # 1.5h window needs 2 hourly entries; only 1 provided
        assert find_cheapest_window(make_prices([0.5])) is None

    def test_finds_correct_start_hour(self):
        # prices at hours 0-4: [0.5, 0.3, 0.1, 0.4, 0.6]
        # i=0: (0.5 + 0.3*0.5) / 1.5 = 0.433
        # i=1: (0.3 + 0.1*0.5) / 1.5 = 0.233
        # i=2: (0.1 + 0.4*0.5) / 1.5 = 0.200  <- cheapest
        # i=3: (0.4 + 0.6*0.5) / 1.5 = 0.467
        result = find_cheapest_window(make_prices([0.5, 0.3, 0.1, 0.4, 0.6]))
        assert result['start'].hour == 2

    def test_window_duration_is_correct(self):
        result = find_cheapest_window(make_prices([0.5, 0.1, 0.3]))
        duration_seconds = (result['end'] - result['start']).total_seconds()
        assert duration_seconds == 1.5 * 3600

    def test_avg_price_is_time_weighted(self):
        # Only 2 prices: p0=0.2, p1=0.4
        # cost = 0.2*1.0 + 0.4*0.5 = 0.40; avg = 0.40 / 1.5
        result = find_cheapest_window(make_prices([0.2, 0.4]))
        expected = (0.2 * 1.0 + 0.4 * 0.5) / 1.5
        assert abs(result['avg_price'] - expected) < 1e-9

    def test_returns_datetime_objects(self):
        result = find_cheapest_window(make_prices([0.3, 0.2, 0.4]))
        assert isinstance(result['start'], datetime)
        assert isinstance(result['end'], datetime)

    def test_handles_unsorted_input(self):
        prices = make_prices([0.5, 0.3, 0.1, 0.4, 0.6])
        shuffled = prices[3:] + prices[:3]
        assert find_cheapest_window(prices)['start'] == find_cheapest_window(shuffled)['start']

    def test_custom_window_hours(self):
        # 2h window over [0.8, 0.1, 0.2]
        # i=0: (0.8+0.1)/2 = 0.45
        # i=1: (0.1+0.2)/2 = 0.15  <- cheapest
        result = find_cheapest_window(make_prices([0.8, 0.1, 0.2]), window_hours=2.0)
        assert result['start'].hour == 1

    def test_all_equal_prices(self):
        result = find_cheapest_window(make_prices([0.3, 0.3, 0.3]))
        assert result is not None
        assert abs(result['avg_price'] - 0.3) < 1e-9


class TestPriceLabel:
    def test_dirt_cheap(self):
        from src.analyze import price_label
        assert price_label(0.15) == 'dirt cheap'   # 15 öre

    def test_cheap(self):
        from src.analyze import price_label
        assert price_label(0.50) == 'cheap'         # 50 öre

    def test_acceptable(self):
        from src.analyze import price_label
        assert price_label(0.85) == 'acceptable'    # 85 öre

    def test_expensive(self):
        from src.analyze import price_label
        assert price_label(1.15) == 'expensive'     # 115 öre

    def test_painful(self):
        from src.analyze import price_label
        assert price_label(1.50) == 'painful'       # 150 öre

    def test_boundary_30_ore_is_cheap_not_dirt_cheap(self):
        from src.analyze import price_label
        assert price_label(0.30) == 'cheap'

    def test_boundary_70_ore_is_acceptable_not_cheap(self):
        from src.analyze import price_label
        assert price_label(0.70) == 'acceptable'

    def test_boundary_exactly_1kr_is_expensive(self):
        from src.analyze import price_label
        assert price_label(1.00) == 'expensive'

    def test_boundary_exactly_130_ore_is_painful(self):
        from src.analyze import price_label
        assert price_label(1.30) == 'painful'


class TestFindCheapStartSpan:
    def test_returns_none_for_empty_list(self):
        assert find_cheap_start_span([]) is None

    def test_returns_none_when_insufficient_data(self):
        assert find_cheap_start_span(make_prices([0.5])) is None

    def test_best_matches_find_cheapest_window(self):
        prices = make_prices([0.5, 0.3, 0.1, 0.4, 0.6])
        span = find_cheap_start_span(prices)
        cheapest = find_cheapest_window(prices)
        assert span['best']['start'] == cheapest['start']
        assert span['best']['end'] == cheapest['end']
        assert abs(span['best']['avg_price'] - cheapest['avg_price']) < 1e-9

    def test_span_collapses_when_neighbours_are_in_different_zone(self):
        # 1.5h windows by index:
        #  i=0: (0.80 + 0.80*0.5) / 1.5 = 0.80 → expensive
        #  i=1: (0.80 + 0.05*0.5) / 1.5 = 0.55 → cheap
        #  i=2: (0.05 + 0.05*0.5) / 1.5 ≈ 0.05 → dirt cheap (best, isolated)
        #  i=3: (0.05 + 0.80*0.5) / 1.5 = 0.30 → cheap
        #  i=4: (0.80 + 0.80*0.5) / 1.5 = 0.80 → expensive
        prices = make_prices([0.80, 0.80, 0.05, 0.05, 0.80, 0.80])
        span = find_cheap_start_span(prices)
        assert span['label'] == 'dirt cheap'
        assert span['earliest_start'] == span['latest_start']
        assert span['earliest_start'].hour == 2

    def test_span_extends_through_neighbouring_same_zone_windows(self):
        # All hours dirt cheap (well below 30 öre): every window labelled dirt cheap.
        prices = make_prices([0.05, 0.10, 0.05, 0.08, 0.04, 0.06])
        span = find_cheap_start_span(prices)
        assert span['label'] == 'dirt cheap'
        assert span['earliest_start'].hour == 0
        assert span['latest_start'].hour == 4  # last possible 1.5h start

    def test_outlier_outside_zone_does_not_split_span_outside_best(self):
        # Best is in the middle; an expensive spike on one side should bound that side
        # but the other side should still extend.
        # values: [1.50, 0.05, 0.05, 0.05, 0.05, 0.05]
        #  i=0: (1.50 + 0.05*0.5) / 1.5 = 1.017 → expensive
        #  i=1: (0.05 + 0.05*0.5) / 1.5 = 0.05  → dirt cheap
        #  i=2..4: dirt cheap
        # Best is one of i=1..4; span = [i=1..i=4], so earliest=hour 1, latest=hour 4.
        prices = make_prices([1.50, 0.05, 0.05, 0.05, 0.05, 0.05])
        span = find_cheap_start_span(prices)
        assert span['label'] == 'dirt cheap'
        assert span['earliest_start'].hour == 1
        assert span['latest_start'].hour == 4

    def test_label_reflects_best_zone_even_when_overall_expensive(self):
        # Everything painful: best is still painful, span covers all start times.
        prices = make_prices([1.40, 1.50, 1.45, 1.55])
        span = find_cheap_start_span(prices)
        assert span['label'] == 'painful'
        assert span['earliest_start'].hour == 0
        assert span['latest_start'].hour == 2


def make_quarter_prices(values_sek, start_hour=0, date='2025-02-25'):
    """Helper: build price list from SEK values, one per 15-minute slot."""
    return [
        {
            'time_start': f'{date}T{(start_hour + i // 4) % 24:02d}:{(i % 4) * 15:02d}:00+01:00',
            'kWh_SEK': price,
        }
        for i, price in enumerate(values_sek)
    ]


class TestQuarterHourlyResolution:
    """
    The feed moved from hourly to 15-minute slots. A window must cover a real
    1.5 hours of data — six quarter-hourly rows — not the first two rows it
    finds.
    """

    # A very cheap but short dip, then a longer genuinely cheap stretch.
    # Counting rows instead of duration picks the dip; counting duration
    # correctly picks the stretch.
    DIP_THEN_STRETCH = [0.05, 0.05, 0.9, 0.9] + [0.2] * 6 + [0.9, 0.9]

    def test_window_covers_six_quarter_hour_slots(self):
        result = find_cheapest_window(make_quarter_prices(self.DIP_THEN_STRETCH))
        # The 30-minute dip is cheaper per-slot but cannot fill 1.5 hours
        assert result['start'].hour == 1
        assert result['start'].minute == 0
        assert result['avg_price'] == pytest.approx(0.2)

    def test_window_end_is_ninety_minutes_after_start(self):
        result = find_cheapest_window(make_quarter_prices(self.DIP_THEN_STRETCH))
        assert (result['end'] - result['start']).total_seconds() == 90 * 60

    def test_returns_none_when_fewer_than_six_slots(self):
        assert find_cheapest_window(make_quarter_prices([0.1] * 5)) is None

    def test_six_slots_is_exactly_enough(self):
        assert find_cheapest_window(make_quarter_prices([0.1] * 6)) is not None

    def test_custom_window_hours_scales_with_resolution(self):
        # 1 hour = 4 quarter-hourly slots
        prices = make_quarter_prices([0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.9, 0.9])
        result = find_cheapest_window(prices, window_hours=1.0)
        assert result['start'].minute == 30
        assert result['avg_price'] == pytest.approx(0.1)

    def test_span_start_times_are_quarter_hourly(self):
        span = find_cheap_start_span(make_quarter_prices(self.DIP_THEN_STRETCH))
        assert span['best']['start'].minute == 0
        assert (span['best']['end'] - span['best']['start']).total_seconds() == 90 * 60


class TestCoverageHours:
    """
    The evening report stitches its 12h window from two days, so a missing day
    still leaves enough rows to draw a chart of only half the night. These
    cover the arithmetic that lets it notice.
    """

    def test_empty_list_covers_nothing(self):
        assert coverage_hours([]) == 0.0

    def test_hourly_rows_count_as_one_hour_each(self):
        assert coverage_hours(make_prices([0.1] * 12)) == 12.0

    def test_quarter_hourly_rows_count_as_a_quarter_each(self):
        assert coverage_hours(make_quarter_prices([0.1] * 48)) == 12.0

    def test_half_populated_window_falls_short(self):
        # 28 quarter-hourly rows = the 00:00-07:00 stretch the evening report
        # was charting on 2026-09-03 while today's prices were missing
        assert coverage_hours(make_quarter_prices([0.1] * 28)) == 7.0

    def test_single_row_does_not_divide_by_zero(self):
        assert coverage_hours(make_prices([0.1])) == 1.0

    def test_unordered_input_is_sorted_first(self):
        prices = make_quarter_prices([0.1] * 8)
        assert coverage_hours(list(reversed(prices))) == 2.0
