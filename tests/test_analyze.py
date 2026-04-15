import pytest
from datetime import datetime
from src.analyze import find_cheapest_window


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
