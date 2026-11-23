import pytest
import os
from unittest.mock import patch, call
from src.chart import generate_price_chart

SAMPLE_PRICES = [
    {'time_start': f'2025-02-25T{h:02d}:00:00+01:00', 'kWh_SEK': 0.10 + h * 0.01}
    for h in range(24)
]


class TestGeneratePriceChart:
    def test_returns_none_for_empty_prices(self, tmp_path):
        result = generate_price_chart([], '2025-02-25', 'SE4', output_dir=str(tmp_path))
        assert result is None

    def test_returns_a_string_path(self, tmp_path):
        with patch('plotly.io.write_image'):
            result = generate_price_chart(SAMPLE_PRICES, '2025-02-25', 'SE4', output_dir=str(tmp_path))
        assert isinstance(result, str)

    def test_output_path_ends_with_png(self, tmp_path):
        with patch('plotly.io.write_image'):
            result = generate_price_chart(SAMPLE_PRICES, '2025-02-25', 'SE4', output_dir=str(tmp_path))
        assert result.endswith('.png')

    def test_output_path_includes_date_and_region(self, tmp_path):
        with patch('plotly.io.write_image'):
            result = generate_price_chart(SAMPLE_PRICES, '2025-02-25', 'SE4', output_dir=str(tmp_path))
        assert '2025-02-25' in result
        assert 'SE4' in result

    def test_calls_write_image_once(self, tmp_path):
        with patch('plotly.io.write_image') as mock_write:
            generate_price_chart(SAMPLE_PRICES, '2025-02-25', 'SE4', output_dir=str(tmp_path))
        mock_write.assert_called_once()

    def test_write_image_receives_png_format(self, tmp_path):
        with patch('plotly.io.write_image') as mock_write:
            generate_price_chart(SAMPLE_PRICES, '2025-02-25', 'SE4', output_dir=str(tmp_path))
        _, kwargs = mock_write.call_args
        assert kwargs.get('format') == 'png'

    def test_creates_output_dir_if_missing(self, tmp_path):
        new_dir = str(tmp_path / 'subdir' / 'charts')
        with patch('plotly.io.write_image'):
            generate_price_chart(SAMPLE_PRICES, '2025-02-25', 'SE4', output_dir=new_dir)
        assert os.path.isdir(new_dir)


class TestPriceColor:
    BANDS = [
        (-0.10, '#2b83ba'),   # almost free
        (0.15, '#1a9850'),    # dirt cheap
        (0.50, '#91cf60'),    # cheap
        (0.85, '#fee08b'),    # acceptable
        (1.20, '#fdae61'),    # pricey
        (1.90, '#f46d43'),    # expensive
        (2.70, '#d73027'),    # painful
        (3.80, '#a50026'),    # brutal
        (7.00, '#7b2d8e'),    # daylight robbery
    ]

    @pytest.mark.parametrize('price,color', BANDS)
    def test_band(self, price, color):
        from src.chart import price_color
        assert price_color(price) == color

    def test_boundary_30_ore_is_cheap_colour(self):
        from src.chart import price_color
        assert price_color(0.30) == '#91cf60'

    def test_boundary_450_ore_is_top_colour(self):
        from src.chart import price_color
        assert price_color(4.50) == '#7b2d8e'

    def test_bands_match_labels(self):
        # Colour and label bands are defined separately; they must not drift.
        from src.analyze import _PRICE_THRESHOLDS
        from src.chart import _COLOR_THRESHOLDS
        assert [t for t, _ in _PRICE_THRESHOLDS] == [t for t, _ in _COLOR_THRESHOLDS]