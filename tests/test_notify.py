import pytest
from unittest.mock import patch, MagicMock
from src.notify import send_message, send_photo

TOKEN = 'fake_token_123'
CHAT_ID = '-100123456789'


class TestSendMessage:
    def test_posts_to_telegram_send_message_endpoint(self):
        with patch('requests.post') as mock_post:
            mock_post.return_value.ok = True
            send_message(TOKEN, CHAT_ID, 'Hello')
        url = mock_post.call_args[0][0]
        assert TOKEN in url
        assert 'sendMessage' in url

    def test_includes_chat_id_and_text_in_payload(self):
        with patch('requests.post') as mock_post:
            mock_post.return_value.ok = True
            send_message(TOKEN, CHAT_ID, 'Test message')
        payload = mock_post.call_args[1]['data']
        assert payload['chat_id'] == CHAT_ID
        assert payload['text'] == 'Test message'

    def test_returns_true_on_success(self):
        with patch('requests.post') as mock_post:
            mock_post.return_value.ok = True
            assert send_message(TOKEN, CHAT_ID, 'Hi') is True

    def test_returns_false_when_response_not_ok(self):
        with patch('requests.post') as mock_post:
            mock_post.return_value.ok = False
            assert send_message(TOKEN, CHAT_ID, 'Hi') is False

    def test_returns_false_on_network_exception(self):
        with patch('requests.post', side_effect=Exception('connection refused')):
            assert send_message(TOKEN, CHAT_ID, 'Hi') is False


class TestSendPhoto:
    def test_posts_to_send_photo_endpoint(self, tmp_path):
        photo = tmp_path / 'chart.png'
        photo.write_bytes(b'\x89PNG\r\n')

        with patch('requests.post') as mock_post:
            mock_post.return_value.ok = True
            send_photo(TOKEN, CHAT_ID, str(photo))
        url = mock_post.call_args[0][0]
        assert 'sendPhoto' in url

    def test_includes_chat_id_in_payload(self, tmp_path):
        photo = tmp_path / 'chart.png'
        photo.write_bytes(b'\x89PNG\r\n')

        with patch('requests.post') as mock_post:
            mock_post.return_value.ok = True
            send_photo(TOKEN, CHAT_ID, str(photo), caption='cap')
        payload = mock_post.call_args[1]['data']
        assert payload['chat_id'] == CHAT_ID

    def test_returns_true_on_success(self, tmp_path):
        photo = tmp_path / 'chart.png'
        photo.write_bytes(b'\x89PNG\r\n')

        with patch('requests.post') as mock_post:
            mock_post.return_value.ok = True
            assert send_photo(TOKEN, CHAT_ID, str(photo)) is True

    def test_returns_false_for_missing_file(self):
        assert send_photo(TOKEN, CHAT_ID, '/no/such/file.png') is False

    def test_returns_false_on_network_exception(self, tmp_path):
        photo = tmp_path / 'chart.png'
        photo.write_bytes(b'\x89PNG\r\n')

        with patch('requests.post', side_effect=Exception('timeout')):
            assert send_photo(TOKEN, CHAT_ID, str(photo)) is False
