"""
Telegram API 單元測試
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.services.telegram_api import TelegramAPI


class TestTelegramAPI:
    """Telegram API 測試類別"""
    
    def setup_method(self):
        """測試設定"""
        with patch('src.services.telegram_api.settings') as mock_settings:
            mock_settings.telegram_bot_token = '123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
            mock_settings.get.return_value = 'https://api.telegram.org/bot'
            self.api = TelegramAPI()
    
    @patch('src.services.telegram_api.settings')
    def test_init(self, mock_settings):
        """測試初始化"""
        mock_settings.telegram_bot_token = 'test_token'
        mock_settings.get.return_value = 'https://test.api.com/bot'
        
        api = TelegramAPI()
        
        assert api.bot_token == 'test_token'
        assert api.api_url == 'https://test.api.com/bot'
        assert api.max_retries == 3
        assert api.retry_delay == 1
        assert api.timeout == 30
    
    @patch('src.services.telegram_api.time.sleep')
    def test_make_request_with_retry_success(self, mock_sleep):
        """測試成功的API請求"""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True, 'result': {}}
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.api.session, 'get', return_value=mock_response):
            result = self.api._make_request_with_retry('GET', 'https://test.com')
            
        assert result == {'ok': True, 'result': {}}
        mock_sleep.assert_not_called()
    
    @patch('src.services.telegram_api.time.sleep')
    def test_make_request_with_retry_timeout_then_success(self, mock_sleep):
        """測試超時後重試成功"""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True, 'result': {}}
        mock_response.raise_for_status.return_value = None
        
        # 第一次請求超時，第二次成功
        side_effects = [requests.exceptions.Timeout(), mock_response]
        
        with patch.object(self.api.session, 'get', side_effect=side_effects):
            result = self.api._make_request_with_retry('GET', 'https://test.com')
            
        assert result == {'ok': True, 'result': {}}
        mock_sleep.assert_called_once_with(1)  # 第一次重試延遲1秒
    
    @patch('src.services.telegram_api.time.sleep')
    def test_make_request_with_retry_rate_limit(self, mock_sleep):
        """測試速率限制處理"""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '5'}
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response_429)
        
        mock_response_success = Mock()
        mock_response_success.json.return_value = {'ok': True, 'result': {}}
        mock_response_success.raise_for_status.return_value = None
        
        side_effects = [mock_response_429, mock_response_success]
        
        with patch.object(self.api.session, 'get', side_effect=side_effects):
            result = self.api._make_request_with_retry('GET', 'https://test.com')
            
        assert result == {'ok': True, 'result': {}}
        mock_sleep.assert_called_with(5)  # 使用Retry-After標頭的值
    
    def test_make_request_with_retry_telegram_api_error(self):
        """測試Telegram API錯誤回應"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': False,
            'error_code': 400,
            'description': '測試錯誤'
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.api.session, 'get', return_value=mock_response):
            result = self.api._make_request_with_retry('GET', 'https://test.com')
            
        # 客戶端錯誤應該直接返回，不重試
        assert result == {'ok': False, 'error_code': 400, 'description': '測試錯誤'}
    
    def test_validate_user_id_valid_numeric(self):
        """測試有效的數字用戶ID"""
        assert self.api.validate_user_id('123456789') is True
        assert self.api.validate_user_id('1') is True
    
    def test_validate_user_id_valid_username(self):
        """測試有效的用戶名"""
        assert self.api.validate_user_id('@username') is True
        assert self.api.validate_user_id('@test_user_123') is True
    
    def test_validate_user_id_invalid(self):
        """測試無效的用戶ID"""
        assert self.api.validate_user_id('') is False
        assert self.api.validate_user_id('0') is False
        assert self.api.validate_user_id('-123') is False
        assert self.api.validate_user_id('abc') is False
        assert self.api.validate_user_id('@') is False
        assert self.api.validate_user_id('@a') is False  # 太短
        assert self.api.validate_user_id('@' + 'a' * 31) is False  # 太長 (32字符總長度)
    
    def test_validate_chat_access_success(self):
        """測試成功驗證聊天存取權限"""
        mock_result = {
            'ok': True,
            'result': {
                'id': 123456789,
                'type': 'private'
            }
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_result):
            result = self.api.validate_chat_access('123456789')
            
        assert result is True
    
    def test_validate_chat_access_failure(self):
        """測試聊天存取權限驗證失敗"""
        mock_result = {
            'ok': False,
            'error_code': 403,
            'description': 'Forbidden: bot was blocked by the user'
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_result):
            result = self.api.validate_chat_access('123456789')
            
        assert result is False
    
    def test_send_notification_success(self):
        """測試成功發送通知"""
        mock_result = {
            'ok': True,
            'result': {
                'message_id': 123,
                'chat': {'id': 123456789}
            }
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_result):
            result = self.api.send_notification('123456789', '測試訊息')
            
        assert result is True
    
    def test_send_notification_no_token(self):
        """測試沒有Bot Token時發送通知"""
        self.api.bot_token = ''
        
        result = self.api.send_notification('123456789', '測試訊息')
        
        assert result is False
    
    def test_send_notification_invalid_user_id(self):
        """測試無效用戶ID"""
        result = self.api.send_notification('invalid_id', '測試訊息')
        
        assert result is False
    
    def test_send_notification_empty_message(self):
        """測試空訊息"""
        result = self.api.send_notification('123456789', '')
        
        assert result is False
    
    def test_send_notification_user_blocked_bot(self):
        """測試用戶封鎖Bot"""
        mock_result = {
            'ok': False,
            'error_code': 403,
            'description': 'Forbidden: bot was blocked by the user'
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_result):
            result = self.api.send_notification('123456789', '測試訊息')
            
        assert result is False
    
    def test_validate_bot_token_success(self):
        """測試成功驗證Bot Token"""
        mock_result = {
            'ok': True,
            'result': {
                'id': 123456789,
                'is_bot': True,
                'first_name': 'Test Bot',
                'username': 'testbot'
            }
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_result):
            result = self.api.validate_bot_token()
            
        assert result is True
    
    def test_validate_bot_token_no_token(self):
        """測試沒有Bot Token"""
        self.api.bot_token = ''
        
        result = self.api.validate_bot_token()
        
        assert result is False
    
    def test_validate_bot_token_invalid_format(self):
        """測試無效的Token格式"""
        self.api.bot_token = 'invalid_token'
        
        result = self.api.validate_bot_token()
        
        assert result is False
    
    def test_validate_bot_token_api_error(self):
        """測試API錯誤"""
        mock_result = {
            'ok': False,
            'error_code': 401,
            'description': 'Unauthorized'
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_result):
            result = self.api.validate_bot_token()
            
        assert result is False
    
    def test_get_bot_info_success(self):
        """測試成功取得Bot資訊"""
        mock_result = {
            'ok': True,
            'result': {
                'id': 123456789,
                'is_bot': True,
                'first_name': 'Test Bot',
                'username': 'testbot'
            }
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_result):
            result = self.api.get_bot_info()
            
        expected = {
            'id': 123456789,
            'is_bot': True,
            'first_name': 'Test Bot',
            'username': 'testbot'
        }
        assert result == expected
    
    def test_get_bot_info_no_token(self):
        """測試沒有Bot Token時取得資訊"""
        self.api.bot_token = ''
        
        result = self.api.get_bot_info()
        
        assert result is None
    
    def test_send_test_message(self):
        """測試發送測試訊息"""
        with patch.object(self.api, 'send_notification', return_value=True) as mock_send:
            result = self.api.send_test_message('123456789')
            
        assert result is True
        mock_send.assert_called_once()
        # 檢查訊息內容包含預期的文字
        call_args = mock_send.call_args[0]
        assert '測試訊息' in call_args[1]
    
    def test_send_match_notification(self):
        """測試發送比賽通知"""
        match_info = {
            'team1': 'T1',
            'team2': 'GenG',
            'tournament': 'LCK Spring',
            'match_time': '2024-01-15 18:00',
            'match_format': 'BO3',
            'stream_url': 'https://twitch.tv/lck'
        }
        
        with patch.object(self.api, 'send_notification', return_value=True) as mock_send:
            result = self.api.send_match_notification('123456789', match_info)
            
        assert result is True
        mock_send.assert_called_once()
        # 檢查訊息內容包含比賽資訊
        call_args = mock_send.call_args[0]
        message = call_args[1]
        assert 'T1' in message
        assert 'GenG' in message
        assert 'LCK Spring' in message
        assert 'BO3' in message
        assert 'twitch.tv/lck' in message
    
    def test_send_match_notification_no_stream(self):
        """測試發送沒有直播連結的比賽通知"""
        match_info = {
            'team1': 'T1',
            'team2': 'GenG',
            'tournament': 'LCK Spring',
            'match_time': '2024-01-15 18:00',
            'match_format': 'BO3'
        }
        
        with patch.object(self.api, 'send_notification', return_value=True) as mock_send:
            result = self.api.send_match_notification('123456789', match_info)
            
        assert result is True
        mock_send.assert_called_once()
        # 檢查訊息不包含直播連結
        call_args = mock_send.call_args[0]
        message = call_args[1]
        assert '觀看直播' not in message
    
    def test_get_webhook_info_success(self):
        """測試成功取得Webhook資訊"""
        mock_result = {
            'ok': True,
            'result': {
                'url': '',
                'has_custom_certificate': False,
                'pending_update_count': 0
            }
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_result):
            result = self.api.get_webhook_info()
            
        expected = {
            'url': '',
            'has_custom_certificate': False,
            'pending_update_count': 0
        }
        assert result == expected
    
    def test_get_webhook_info_no_token(self):
        """測試沒有Bot Token時取得Webhook資訊"""
        self.api.bot_token = ''
        
        result = self.api.get_webhook_info()
        
        assert result is None