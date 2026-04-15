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
