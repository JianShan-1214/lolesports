"""
Leaguepedia API 單元測試
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests

from src.services.leaguepedia_api import LeaguepediaAPI
from src.models.team import Team
from src.models.match import Match


class TestLeaguepediaAPI:
    """Leaguepedia API 測試類別"""
    
    def setup_method(self):
        """測試設定"""
        self.api = LeaguepediaAPI()
    
    @patch('src.services.leaguepedia_api.settings')
    def test_init(self, mock_settings):
        """測試初始化"""
        mock_settings.get.side_effect = lambda key, default=None: {
            'leaguepedia.api_url': 'https://test.api.com',
            'leaguepedia.user_agent': 'Test-Agent/1.0'
        }.get(key, default)
        
        api = LeaguepediaAPI()
        
        assert api.api_url == 'https://test.api.com'
        assert api.user_agent == 'Test-Agent/1.0'
        assert api.max_retries == 3
        assert api.retry_delay == 1
        assert api.timeout == 30
    
    @patch('src.services.leaguepedia_api.time.sleep')
    def test_make_request_with_retry_success(self, mock_sleep):
        """測試成功的API請求"""
        mock_response = Mock()
        mock_response.json.return_value = {'cargoquery': []}
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.api.session, 'get', return_value=mock_response):
            result = self.api._make_request_with_retry({'test': 'params'})
            
        assert result == {'cargoquery': []}
        mock_sleep.assert_not_called()
    
    @patch('src.services.leaguepedia_api.time.sleep')
    def test_make_request_with_retry_timeout_then_success(self, mock_sleep):
        """測試超時後重試成功"""
        mock_response = Mock()
        mock_response.json.return_value = {'cargoquery': []}
        mock_response.raise_for_status.return_value = None
        
        # 第一次請求超時，第二次成功
        side_effects = [requests.exceptions.Timeout(), mock_response]
        
        with patch.object(self.api.session, 'get', side_effect=side_effects):
            result = self.api._make_request_with_retry({'test': 'params'})
            
        assert result == {'cargoquery': []}
        mock_sleep.assert_called_once_with(1)  # 第一次重試延遲1秒
    
    @patch('src.services.leaguepedia_api.time.sleep')
    def test_make_request_with_retry_max_retries_exceeded(self, mock_sleep):
        """測試超過最大重試次數"""
        with patch.object(self.api.session, 'get', side_effect=requests.exceptions.Timeout()):
            with pytest.raises(requests.exceptions.Timeout):
                self.api._make_request_with_retry({'test': 'params'})
        
        # 應該重試3次，所以sleep被調用2次（第1次和第2次重試之間）
        assert mock_sleep.call_count == 2
    
    @patch('src.services.leaguepedia_api.time.sleep')
    def test_make_request_with_retry_rate_limit(self, mock_sleep):
        """測試速率限制處理"""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response_429)
        
        mock_response_success = Mock()
        mock_response_success.json.return_value = {'cargoquery': []}
        mock_response_success.raise_for_status.return_value = None
        
        side_effects = [mock_response_429, mock_response_success]
        
        with patch.object(self.api.session, 'get', side_effect=side_effects):
            result = self.api._make_request_with_retry({'test': 'params'})
            
        assert result == {'cargoquery': []}
        # 速率限制會觸發兩次 sleep：一次是速率限制處理，一次是重試間隔
        assert mock_sleep.call_count >= 1
    
    def test_make_request_with_retry_api_error(self):
        """測試API回應錯誤"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': {'info': '測試錯誤訊息'}
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.api.session, 'get', return_value=mock_response):
            with pytest.raises(requests.RequestException, match="API錯誤: 測試錯誤訊息"):
                self.api._make_request_with_retry({'test': 'params'})
    
    def test_get_upcoming_matches_success(self):
        """測試成功取得比賽資料"""
        mock_data = {
            'cargoquery': [
                {
                    'title': {
                        'UniqueGame': 'test_match_1',
                        'Team1': 'T1',
                        'Team2': 'GenG',
                        'DateTime UTC': '2024-01-15 18:00:00',
                        'Tournament': 'LCK Spring',
                        'BestOf': '3',
                        'T1.Region': 'Korea',
                        'T2.Region': 'Korea',
                        'Stream': 'https://twitch.tv/lck'
                    }
                }
            ]
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_data):
            matches = self.api.get_upcoming_matches(days=2)
            
        assert len(matches) == 1
        match = matches[0]
        assert match.match_id == 'test_match_1'
        assert match.team1.name == 'T1'
        assert match.team2.name == 'GenG'
        assert match.tournament == 'LCK Spring'
        assert match.match_format == 'BO3'
        assert match.stream_url == 'https://twitch.tv/lck'
    
    def test_get_upcoming_matches_api_failure(self):
        """測試API請求失敗"""
        with patch.object(self.api, '_make_request_with_retry', return_value=None):
            matches = self.api.get_upcoming_matches(days=2)
            
        assert matches == []
    
    def test_get_team_list_success(self):
        """測試成功取得戰隊列表"""
        mock_data = {
            'cargoquery': [
                {
                    'title': {
                        'OverviewPage': 'T1',
                        'Name': 'T1',
                        'Region': 'Korea',
                        'League': 'LCK'
                    }
                },
                {
                    'title': {
                        'OverviewPage': 'GenG',
                        'Name': 'Gen.G',
                        'Region': 'Korea',
                        'League': 'LCK'
                    }
                }
            ]
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_data):
            teams = self.api.get_team_list()
            
        assert len(teams) == 2
        assert teams[0].name == 'T1'
        assert teams[1].name == 'Gen.G'
        assert all(team.region == 'Korea' for team in teams)
    
    def test_get_match_details_success(self):
        """測試成功取得比賽詳情"""
        mock_data = {
            'cargoquery': [
                {
                    'title': {
                        'UniqueGame': 'test_match_1',
                        'Team1': 'T1',
                        'Team2': 'GenG',
                        'DateTime UTC': '2024-01-15 18:00:00',
                        'Tournament': 'LCK Spring',
                        'BestOf': '3',
                        'T1.Region': 'Korea',
                        'T2.Region': 'Korea'
                    }
                }
            ]
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_data):
            match = self.api.get_match_details('test_match_1')
            
        assert match is not None
        assert match.match_id == 'test_match_1'
        assert match.team1.name == 'T1'
        assert match.team2.name == 'GenG'
    
    def test_get_match_details_not_found(self):
        """測試找不到比賽"""
        mock_data = {'cargoquery': []}
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_data):
            match = self.api.get_match_details('nonexistent_match')
            
        assert match is None
    
    def test_parse_match_data_success(self):
        """測試成功解析比賽資料"""
        match_data = {
            'UniqueGame': 'test_match_1',
            'Team1': 'T1',
            'Team2': 'GenG',
            'DateTime UTC': '2024-01-15 18:00:00',
            'Tournament': 'LCK Spring',
            'BestOf': '3',
            'T1.Region': 'Korea',
            'T2.Region': 'Korea',
            'Stream': 'https://twitch.tv/lck'
        }
        
        match = self.api._parse_match_data(match_data)
        
        assert match is not None
        assert match.match_id == 'test_match_1'
        assert match.team1.name == 'T1'
        assert match.team2.name == 'GenG'
        assert match.scheduled_time == datetime(2024, 1, 15, 18, 0, 0)
        assert match.tournament == 'LCK Spring'
        assert match.match_format == 'BO3'
        assert match.stream_url == 'https://twitch.tv/lck'
    
    def test_parse_match_data_missing_required_fields(self):
        """測試缺少必要欄位的比賽資料"""
        match_data = {
            'Team1': 'T1',
            # 缺少 Team2 和 UniqueGame
            'DateTime UTC': '2024-01-15 18:00:00',
            'Tournament': 'LCK Spring'
        }
        
        match = self.api._parse_match_data(match_data)
        
        assert match is None
    
    def test_parse_match_data_invalid_datetime(self):
        """測試無效的時間格式"""
        match_data = {
            'UniqueGame': 'test_match_1',
            'Team1': 'T1',
            'Team2': 'GenG',
            'DateTime UTC': 'invalid_datetime',
            'Tournament': 'LCK Spring',
            'BestOf': '3',
            'T1.Region': 'Korea',
            'T2.Region': 'Korea'
        }
        
        match = self.api._parse_match_data(match_data)
        
        # 應該使用當前時間作為預設值
        assert match is not None
        assert match.match_id == 'test_match_1'
        assert isinstance(match.scheduled_time, datetime)
    
    def test_parse_team_data_success(self):
        """測試成功解析戰隊資料"""
        team_data = {
            'OverviewPage': 'T1',
            'Name': 'T1',
            'Region': 'Korea',
            'League': 'LCK'
        }
        
        team = self.api._parse_team_data(team_data)
        
        assert team is not None
        assert team.team_id == 'T1'
        assert team.name == 'T1'
        assert team.region == 'Korea'
        assert team.league == 'LCK'
    
    def test_parse_team_data_missing_required_fields(self):
        """測試缺少必要欄位的戰隊資料"""
        team_data = {
            'OverviewPage': 'T1',
            # 缺少 Name
            'Region': 'Korea'
        }
        
        team = self.api._parse_team_data(team_data)
        
        assert team is None
    
    def test_validate_connection_success(self):
        """測試成功驗證連接"""
        mock_data = {
            'query': {
                'general': {
                    'sitename': 'Leaguepedia'
                }
            }
        }
        
        with patch.object(self.api, '_make_request_with_retry', return_value=mock_data):
            result = self.api.validate_connection()
            
        assert result is True
    
    def test_validate_connection_failure(self):
        """測試連接驗證失敗"""
        with patch.object(self.api, '_make_request_with_retry', return_value=None):
            result = self.api.validate_connection()
            
        assert result is False