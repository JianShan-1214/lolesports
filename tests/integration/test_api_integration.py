"""
外部API整合測試
測試與Leaguepedia API和Telegram Bot API的整合
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime, timedelta
import json

from src.services.leaguepedia_api import LeaguepediaAPI
from src.services.telegram_api import TelegramAPI
from src.models.team import Team
from src.models.match import Match

from tests.fixtures.test_data import IntegrationTestHelper


class TestLeaguepediaAPIIntegration:
    """Leaguepedia API整合測試"""
    
    def setup_method(self):
        """設定測試環境"""
        self.api = LeaguepediaAPI()
    
    @patch('src.services.leaguepedia_api.LeaguepediaAPI._make_request_with_retry')
    def test_get_upcoming_matches_success(self, mock_make_request, mock_api_responses):
        """測試成功獲取即將到來的比賽"""
        
        # 模擬成功的API回應（使用正確的Cargo API格式）
        mock_make_request.return_value = {
            "cargoquery": [
                {
                    "title": {
                        "Team1": "T1",
                        "Team2": "Gen.G",
                        "DateTime UTC": "2025-12-20 18:00:00",  # 注意：使用空格而不是底線
                        "OverviewPage": "LCK Spring 2025",
                        "BestOf": "3",
                        "Stream": "https://twitch.tv/lck",
                        "Winner": ""
                    }
                },
                {
                    "title": {
                        "Team1": "DRX",
                        "Team2": "T1", 
                        "DateTime UTC": "2025-12-21 18:00:00",  # 注意：使用空格而不是底線
                        "OverviewPage": "LCK Spring 2025",
                        "BestOf": "3",
                        "Stream": "https://twitch.tv/lck",
                        "Winner": ""
                    }
                }
            ]
        }
        
        # 執行API調用
        matches = self.api.get_upcoming_matches(days=2)
        
        # 驗證結果
        assert len(matches) == 2
        assert isinstance(matches[0], Match)
        assert matches[0].team1.name == "T1"
        assert matches[0].team2.name == "Gen.G"
        assert matches[0].tournament == "LCK Spring 2025"
        assert matches[0].match_format == "BO3"
        
        # 驗證API調用
        mock_make_request.assert_called()
        
        print("✅ Leaguepedia API獲取比賽測試通過")
    
    @patch('src.services.leaguepedia_api.LeaguepediaAPI._make_request_with_retry')
    def test_get_upcoming_matches_api_error(self, mock_make_request):
        """測試API錯誤處理"""
        
        # 模擬API錯誤
        mock_make_request.side_effect = Exception("API服務錯誤")
        
        # 執行API調用
        matches = self.api.get_upcoming_matches(days=2)
        
        # 應該返回模擬資料而不是拋出異常
        assert isinstance(matches, list)
        assert len(matches) > 0  # 會返回模擬資料
        
        print("✅ Leaguepedia API錯誤處理測試通過")
    
    @patch('src.services.leaguepedia_api.LeaguepediaAPI._make_request_with_retry')
    def test_get_upcoming_matches_timeout(self, mock_make_request):
        """測試API超時處理"""
        
        # 模擬超時
        mock_make_request.side_effect = requests.Timeout("Request timeout")
        
        # 執行API調用
        matches = self.api.get_upcoming_matches(days=2)
        
        # 應該返回模擬資料
        assert isinstance(matches, list)
        assert len(matches) > 0  # 會返回模擬資料
        
        print("✅ Leaguepedia API超時處理測試通過")
    
    @patch('requests.Session.get')
    def test_get_team_list_success(self, mock_get):
        """測試成功獲取戰隊列表"""
        
        # 模擬成功的API回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": {
                "results": {
                    "Teams": [
                        {
                            "team_id": "t1",
                            "name": "T1",
                            "region": "KR",
                            "league": "LCK"
                        },
                        {
                            "team_id": "geng",
                            "name": "Gen.G",
                            "region": "KR",
                            "league": "LCK"
                        },
                        {
                            "team_id": "fnatic",
                            "name": "Fnatic",
                            "region": "EU",
                            "league": "LEC"
                        }
                    ]
                }
            }
        }
        mock_get.return_value = mock_response
        
        # 執行API調用
        teams = self.api.get_team_list()
        
        # 驗證結果
        assert len(teams) == 3
        assert isinstance(teams[0], Team)
        assert teams[0].name == "T1"
        assert teams[0].region == "KR"
        assert teams[0].league == "LCK"
        
        print("✅ Leaguepedia API獲取戰隊列表測試通過")
    
    @patch('requests.Session.get')
    def test_get_match_details_success(self, mock_get):
        """測試成功獲取比賽詳情"""
        
        # 模擬成功的API回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": {
                "results": {
                    "Matches": [
                        {
                            "match_id": "match_001",
                            "team1": "T1",
                            "team2": "Gen.G",
                            "datetime_utc": "2025-12-20 18:00:00",
                            "tournament": "LCK Spring 2025",
                            "bestof": "3",
                            "status": "scheduled",
                            "stream": "https://twitch.tv/lck",
                            "game1_winner": "",
                            "game2_winner": "",
                            "game3_winner": ""
                        }
                    ]
                }
            }
        }
        mock_get.return_value = mock_response
        
        # 執行API調用
        match = self.api.get_match_details("match_001")
        
        # 驗證結果
        assert match is not None
        assert isinstance(match, Match)
        assert match.match_id == "match_001"
        assert match.team1.name == "T1"
        assert match.team2.name == "Gen.G"
        
        print("✅ Leaguepedia API獲取比賽詳情測試通過")
    
    @patch('requests.Session.get')
    def test_api_retry_mechanism(self, mock_get):
        """測試API重試機制"""
        
        # 模擬第一次失敗，第二次成功
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503
        mock_response_fail.raise_for_status.side_effect = requests.HTTPError("Service Unavailable")
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "query": {
                "results": {
                    "Teams": [
                        {
                            "team_id": "t1",
                            "name": "T1",
                            "region": "KR",
                            "league": "LCK"
                        }
                    ]
                }
            }
        }
        
        mock_get.side_effect = [mock_response_fail, mock_response_success]
        
        # 執行API調用
        teams = self.api.get_team_list()
        
        # 驗證重試成功
        assert len(teams) == 1
        assert teams[0].name == "T1"
        
        # 驗證調用了兩次（第一次失敗，第二次成功）
        assert mock_get.call_count == 2
        
        print("✅ Leaguepedia API重試機制測試通過")


class TestTelegramAPIIntegration:
    """Telegram Bot API整合測試"""
    
    def setup_method(self):
        """設定測試環境"""
        self.api = TelegramAPI()
    
    @patch('requests.Session.post')
    def test_send_notification_success(self, mock_post, mock_api_responses):
        """測試成功發送通知"""
        
        # 模擬成功的API回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_responses["telegram_success"]
        mock_post.return_value = mock_response
        
        # 執行發送通知
        result = self.api.send_notification("123456789", "測試通知訊息")
        
        # 驗證結果
        assert result is True
        
        # 驗證API調用參數
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "sendMessage" in call_args[0][0]  # URL包含sendMessage
        
        # 驗證請求內容
        request_data = call_args[1]['json']
        assert request_data['chat_id'] == "123456789"
        assert request_data['text'] == "測試通知訊息"
        assert request_data['parse_mode'] == 'HTML'
        
        print("✅ Telegram API發送通知測試通過")
    
    @patch('requests.Session.post')
    def test_send_notification_user_blocked_bot(self, mock_post, mock_api_responses):
        """測試用戶封鎖Bot的情況"""
        
        # 模擬用戶封鎖Bot的回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_responses["telegram_error"]
        mock_post.return_value = mock_response
        
        # 執行發送通知
        result = self.api.send_notification("123456789", "測試通知訊息")
        
        # 應該返回False
        assert result is False
        
        print("✅ Telegram API用戶封鎖處理測試通過")
    
    @patch('requests.Session.post')
    def test_send_notification_rate_limit(self, mock_post):
        """測試速率限制處理"""
        
        # 模擬速率限制回應
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '1'}
        mock_response.raise_for_status.side_effect = requests.HTTPError("Too Many Requests")
        
        # 第二次調用成功
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        
        mock_post.side_effect = [mock_response, mock_response_success]
        
        # 執行發送通知
        result = self.api.send_notification("123456789", "測試通知訊息")
        
        # 應該在重試後成功
        assert result is True
        assert mock_post.call_count == 2
        
        print("✅ Telegram API速率限制處理測試通過")
    
    @patch('requests.Session.get')
    def test_validate_bot_token_success(self, mock_get, mock_api_responses):
        """測試Bot Token驗證成功"""
        
        # 模擬成功的API回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_responses["telegram_bot_info"]
        mock_get.return_value = mock_response
        
        # 執行Token驗證
        result = self.api.validate_bot_token()
        
        # 驗證結果
        assert result is True
        
        # 驗證API調用
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "getMe" in call_args[0][0]
        
        print("✅ Telegram Bot Token驗證測試通過")
    
    @patch('requests.Session.get')
    def test_validate_bot_token_invalid(self, mock_get):
        """測試無效Bot Token"""
        
        # 模擬無效Token的回應
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 401,
            "description": "Unauthorized"
        }
        mock_get.return_value = mock_response
        
        # 執行Token驗證
        result = self.api.validate_bot_token()
        
        # 應該返回False
        assert result is False
        
        print("✅ Telegram無效Token處理測試通過")
    
    def test_validate_user_id_formats(self):
        """測試用戶ID格式驗證"""
        
        # 測試有效的用戶ID格式
        valid_ids = [
            "123456789",
            "987654321",
            "@valid_username",
            "@test_user_123"
        ]
        
        for user_id in valid_ids:
            result = self.api.validate_user_id(user_id)
            assert result is True, f"用戶ID {user_id} 應該是有效的"
        
        # 測試無效的用戶ID格式
        invalid_ids = [
            "",
            "abc",
            "@",
            "@ab",  # 太短
            "@" + "a" * 32,  # 太長
            "0",  # 零不是有效的Telegram ID
            "-123"  # 負數不是有效的Telegram ID
        ]
        
        for user_id in invalid_ids:
            result = self.api.validate_user_id(user_id)
            assert result is False, f"用戶ID {user_id} 應該是無效的"
        
        print("✅ Telegram用戶ID格式驗證測試通過")
    
    @patch('requests.Session.get')
    def test_validate_chat_access_success(self, mock_get):
        """測試聊天存取權限驗證成功"""
        
        # 模擬成功的getChat回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "id": 123456789,
                "type": "private",
                "username": "test_user"
            }
        }
        mock_get.return_value = mock_response
        
        # 執行聊天存取驗證
        result = self.api.validate_chat_access("123456789")
        
        # 驗證結果
        assert result is True
        
        print("✅ Telegram聊天存取驗證測試通過")
    
    @patch('requests.Session.post')
    def test_send_test_message(self, mock_post):
        """測試發送測試訊息"""
        
        # 模擬成功回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        mock_post.return_value = mock_response
        
        # 執行發送測試訊息
        result = self.api.send_test_message("123456789")
        
        # 驗證結果
        assert result is True
        
        # 驗證訊息內容包含測試相關文字
        call_args = mock_post.call_args
        request_data = call_args[1]['json']
        message_text = request_data['text']
        assert "測試訊息" in message_text
        assert "通知功能正常運作" in message_text
        
        print("✅ Telegram測試訊息發送測試通過")


class TestAPIErrorHandling:
    """API錯誤處理測試"""
    
    def setup_method(self):
        """設定測試環境"""
        self.leaguepedia_api = LeaguepediaAPI()
        self.telegram_api = TelegramAPI()
    
    @patch('requests.Session.get')
    def test_network_connection_error(self, mock_get):
        """測試網路連接錯誤處理"""
        
        # 模擬網路連接錯誤
        mock_get.side_effect = requests.ConnectionError("Network connection failed")
        
        # 測試Leaguepedia API
        matches = self.leaguepedia_api.get_upcoming_matches(days=1)
        assert matches == []
        
        teams = self.leaguepedia_api.get_team_list()
        assert teams == []
        
        print("✅ 網路連接錯誤處理測試通過")
    
    @patch('requests.Session.post')
    def test_telegram_network_error(self, mock_post):
        """測試Telegram網路錯誤處理"""
        
        # 模擬網路錯誤
        mock_post.side_effect = requests.ConnectionError("Network connection failed")
        
        # 執行發送通知
        result = self.telegram_api.send_notification("123456789", "測試訊息")
        
        # 應該返回False而不是拋出異常
        assert result is False
        
        print("✅ Telegram網路錯誤處理測試通過")
    
    @patch('requests.Session.get')
    def test_json_parsing_error(self, mock_get):
        """測試JSON解析錯誤處理"""
        
        # 模擬無效的JSON回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response
        
        # 執行API調用
        teams = self.leaguepedia_api.get_team_list()
        
        # 應該返回空列表
        assert teams == []
        
        print("✅ JSON解析錯誤處理測試通過")
    
    @patch('requests.Session.get')
    @patch('requests.Session.post')
    def test_api_timeout_handling(self, mock_post, mock_get):
        """測試API超時處理"""
        
        # 模擬超時
        mock_get.side_effect = requests.Timeout("Request timeout")
        mock_post.side_effect = requests.Timeout("Request timeout")
        
        # 測試Leaguepedia API超時
        matches = self.leaguepedia_api.get_upcoming_matches(days=1)
        assert matches == []
        
        # 測試Telegram API超時
        result = self.telegram_api.send_notification("123456789", "測試訊息")
        assert result is False
        
        print("✅ API超時處理測試通過")