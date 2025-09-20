"""
背景任務調度管理模組單元測試
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.scheduler_manager import SchedulerManager
from src.models.team import Team
from src.models.match import Match


class TestSchedulerManager:
    """背景任務調度管理類別測試"""
    
    def setup_method(self):
        """設定測試環境"""
        # 建立模擬的依賴項目
        self.mock_data_manager = Mock()
        self.mock_leaguepedia_api = Mock()
        self.mock_notification_manager = Mock()
        self.mock_scheduler = Mock()
        
        # 建立調度管理器實例並注入模擬依賴
        with patch('src.services.scheduler_manager.BackgroundScheduler') as mock_scheduler_class:
            mock_scheduler_class.return_value = self.mock_scheduler
            self.scheduler_manager = SchedulerManager()
            
        self.scheduler_manager.data_manager = self.mock_data_manager
        self.scheduler_manager.leaguepedia_api = self.mock_leaguepedia_api
        self.scheduler_manager.notification_manager = self.mock_notification_manager
        
        # 建立測試資料
        self.team1 = Team(
            team_id="t1",
            name="T1",
            region="KR",
            league="LCK"
        )
        
        self.team2 = Team(
            team_id="geng",
            name="Gen.G",
            region="KR",
            league="LCK"
        )
        
        self.match = Match(
            match_id="match_001",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime.now() + timedelta(hours=1),
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
    
    @patch('src.services.scheduler_manager.settings')
    def test_start_background_tasks_success(self, mock_settings):
        """測試成功啟動背景任務"""
        # 設定配置模擬值
        mock_settings.get.side_effect = lambda key, default: {
            'scheduler.match_data_fetch_interval': 30,
            'scheduler.notification_check_interval': 5
        }.get(key, default)
        
        # 執行測試
        self.scheduler_manager.start_background_tasks()
        
        # 驗證調度器操作
        assert self.mock_scheduler.add_job.call_count == 3  # 三個任務
        self.mock_scheduler.start.assert_called_once()
        assert self.scheduler_manager._is_running is True
    
    def test_start_background_tasks_already_running(self):
        """測試當背景任務已經在運行時的行為"""
        # 設定為已運行狀態
        self.scheduler_manager._is_running = True
        
        # 執行測試
        self.scheduler_manager.start_background_tasks()
        
        # 驗證不會重複啟動
        self.mock_scheduler.start.assert_not_called()
    
    @patch('src.services.scheduler_manager.settings')
    def test_schedule_match_data_fetch(self, mock_settings):
        """測試排程比賽資料獲取任務"""
        # 設定配置模擬值
        mock_settings.get.return_value = 30
        
        # 執行測試
        self.scheduler_manager.schedule_match_data_fetch()
        
        # 驗證任務新增
        self.mock_scheduler.add_job.assert_called_once()
        call_args = self.mock_scheduler.add_job.call_args
        
        assert call_args[1]['id'] == 'fetch_match_data'
        assert call_args[1]['name'] == '獲取比賽資料'
        assert call_args[1]['replace_existing'] is True
    
    @patch('src.services.scheduler_manager.settings')
    def test_schedule_notification_check(self, mock_settings):
        """測試排程通知檢查任務"""
        # 設定配置模擬值
        mock_settings.get.return_value = 5
        
        # 執行測試
        self.scheduler_manager.schedule_notification_check()
        
        # 驗證任務新增
        self.mock_scheduler.add_job.assert_called_once()
        call_args = self.mock_scheduler.add_job.call_args
        
        assert call_args[1]['id'] == 'check_notifications'
        assert call_args[1]['name'] == '檢查即將開始的比賽'
        assert call_args[1]['replace_existing'] is True
    
    def test_schedule_retry_failed_notifications(self):
        """測試排程失敗通知重試任務"""
        # 執行測試
        self.scheduler_manager.schedule_retry_failed_notifications()
        
        # 驗證任務新增
        self.mock_scheduler.add_job.assert_called_once()
        call_args = self.mock_scheduler.add_job.call_args
        
        assert call_args[1]['id'] == 'retry_failed_notifications'
        assert call_args[1]['name'] == '重試失敗通知'
        assert call_args[1]['replace_existing'] is True
    
    def test_fetch_match_data_job_success(self):
        """測試比賽資料獲取任務成功執行"""
        # 設定模擬回傳值
        test_matches = [self.match]
        self.mock_leaguepedia_api.get_upcoming_matches.return_value = test_matches
        self.mock_data_manager.cache_match_data.return_value = True
        
        # 執行測試
        self.scheduler_manager._fetch_match_data_job()
        
        # 驗證API呼叫
        self.mock_leaguepedia_api.get_upcoming_matches.assert_called_once_with(days=2)
        self.mock_data_manager.cache_match_data.assert_called_once_with(test_matches)
    
    def test_fetch_match_data_job_no_matches(self):
        """測試比賽資料獲取任務沒有比賽資料"""
        # 設定模擬回傳值
        self.mock_leaguepedia_api.get_upcoming_matches.return_value = []
        
        # 執行測試
        self.scheduler_manager._fetch_match_data_job()
        
        # 驗證不會嘗試快取空資料
        self.mock_data_manager.cache_match_data.assert_not_called()
    
    def test_fetch_match_data_job_cache_failure(self):
        """測試比賽資料獲取任務快取失敗"""
        # 設定模擬回傳值
        test_matches = [self.match]
        self.mock_leaguepedia_api.get_upcoming_matches.return_value = test_matches
        self.mock_data_manager.cache_match_data.return_value = False
        
        # 執行測試
        self.scheduler_manager._fetch_match_data_job()
        
        # 驗證仍會嘗試快取
        self.mock_data_manager.cache_match_data.assert_called_once_with(test_matches)
    
    @patch('src.services.scheduler_manager.datetime')
    def test_check_upcoming_matches_job_with_upcoming_match(self, mock_datetime):
        """測試檢查即將開始的比賽任務（有即將開始的比賽）"""
        # 設定當前時間
        now = datetime(2024, 1, 15, 17, 0)  # 17:00
        mock_datetime.now.return_value = now
        
        # 建立即將在1小時後開始的比賽
        upcoming_match = Match(
            match_id="match_upcoming",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 18, 0),  # 18:00，1小時後
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        # 建立不在通知範圍內的比賽
        far_future_match = Match(
            match_id="match_far",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 20, 0),  # 20:00，3小時後
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        # 設定模擬回傳值
        self.mock_data_manager.get_cached_matches.return_value = [upcoming_match, far_future_match]
        
        # 執行測試
        self.scheduler_manager._check_upcoming_matches_job()
        
        # 驗證只為即將開始的比賽發送通知
        self.mock_notification_manager.send_notifications_for_match.assert_called_once_with(upcoming_match)
    
    @patch('src.services.scheduler_manager.datetime')
    def test_check_upcoming_matches_job_no_upcoming_matches(self, mock_datetime):
        """測試檢查即將開始的比賽任務（沒有即將開始的比賽）"""
        # 設定當前時間
        now = datetime(2024, 1, 15, 17, 0)
        mock_datetime.now.return_value = now
        
        # 建立不在通知範圍內的比賽
        far_future_match = Match(
            match_id="match_far",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 20, 0),  # 3小時後
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        past_match = Match(
            match_id="match_past",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 16, 0),  # 1小時前
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="completed"
        )
        
        # 設定模擬回傳值
        self.mock_data_manager.get_cached_matches.return_value = [far_future_match, past_match]
        
        # 執行測試
        self.scheduler_manager._check_upcoming_matches_job()
        
        # 驗證沒有發送通知
        self.mock_notification_manager.send_notifications_for_match.assert_not_called()
    
    def test_retry_failed_notifications_job(self):
        """測試重試失敗通知任務"""
        # 執行測試
        self.scheduler_manager._retry_failed_notifications_job()
        
        # 驗證呼叫重試方法
        self.mock_notification_manager.retry_failed_notifications.assert_called_once()
    
    def test_stop_all_tasks_when_running(self):
        """測試停止背景任務（當任務正在運行時）"""
        # 設定為運行狀態
        self.scheduler_manager._is_running = True
        
        # 執行測試
        self.scheduler_manager.stop_all_tasks()
        
        # 驗證調度器停止
        self.mock_scheduler.shutdown.assert_called_once()
        assert self.scheduler_manager._is_running is False
    
    def test_stop_all_tasks_when_not_running(self):
        """測試停止背景任務（當任務未運行時）"""
        # 設定為未運行狀態
        self.scheduler_manager._is_running = False
        
        # 執行測試
        self.scheduler_manager.stop_all_tasks()
        
        # 驗證不會嘗試停止調度器
        self.mock_scheduler.shutdown.assert_not_called()
    
    def test_get_job_status_with_jobs(self):
        """測試取得任務狀態（有任務時）"""
        # 建立模擬任務
        mock_job1 = Mock()
        mock_job1.id = 'fetch_match_data'
        mock_job1.name = '獲取比賽資料'
        mock_job1.next_run_time = datetime(2024, 1, 15, 18, 0)
        mock_job1.trigger = 'interval[0:30:00]'
        
        mock_job2 = Mock()
        mock_job2.id = 'check_notifications'
        mock_job2.name = '檢查即將開始的比賽'
        mock_job2.next_run_time = None
        mock_job2.trigger = 'interval[0:05:00]'
        
        # 設定模擬回傳值
        self.mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        self.scheduler_manager._is_running = True
        
        # 執行測試
        status = self.scheduler_manager.get_job_status()
        
        # 驗證結果
        assert status['is_running'] is True
        assert len(status['jobs']) == 2
        assert status['jobs']['fetch_match_data']['name'] == '獲取比賽資料'
        assert status['jobs']['fetch_match_data']['next_run_time'] == '2024-01-15T18:00:00'
        assert status['jobs']['check_notifications']['next_run_time'] is None
    
    def test_get_job_status_no_jobs(self):
        """測試取得任務狀態（沒有任務時）"""
        # 設定模擬回傳值
        self.mock_scheduler.get_jobs.return_value = []
        self.scheduler_manager._is_running = False
        
        # 執行測試
        status = self.scheduler_manager.get_job_status()
        
        # 驗證結果
        assert status['is_running'] is False
        assert len(status['jobs']) == 0
    
    @patch('src.services.scheduler_manager.logger')
    def test_fetch_match_data_job_exception_handling(self, mock_logger):
        """測試比賽資料獲取任務的異常處理"""
        # 設定模擬拋出異常
        self.mock_leaguepedia_api.get_upcoming_matches.side_effect = Exception("API錯誤")
        
        # 執行測試
        self.scheduler_manager._fetch_match_data_job()
        
        # 驗證錯誤日誌記錄
        mock_logger.error.assert_called_once()
        assert "執行比賽資料獲取任務時發生錯誤" in str(mock_logger.error.call_args)
    
    @patch('src.services.scheduler_manager.logger')
    def test_check_upcoming_matches_job_exception_handling(self, mock_logger):
        """測試檢查即將開始比賽任務的異常處理"""
        # 設定模擬拋出異常
        self.mock_data_manager.get_cached_matches.side_effect = Exception("資料庫錯誤")
        
        # 執行測試
        self.scheduler_manager._check_upcoming_matches_job()
        
        # 驗證錯誤日誌記錄
        mock_logger.error.assert_called_once()
        assert "檢查即將開始的比賽時發生錯誤" in str(mock_logger.error.call_args)
    
    @patch('src.services.scheduler_manager.logger')
    def test_retry_failed_notifications_job_exception_handling(self, mock_logger):
        """測試重試失敗通知任務的異常處理"""
        # 設定模擬拋出異常
        self.mock_notification_manager.retry_failed_notifications.side_effect = Exception("重試錯誤")
        
        # 執行測試
        self.scheduler_manager._retry_failed_notifications_job()
        
        # 驗證錯誤日誌記錄
        mock_logger.error.assert_called_once()
        assert "重試失敗通知時發生錯誤" in str(mock_logger.error.call_args)
    
    @patch('src.services.scheduler_manager.logger')
    def test_start_background_tasks_exception_handling(self, mock_logger):
        """測試啟動背景任務的異常處理"""
        # 設定模擬拋出異常
        self.mock_scheduler.start.side_effect = Exception("調度器啟動錯誤")
        
        # 執行測試
        self.scheduler_manager.start_background_tasks()
        
        # 驗證錯誤日誌記錄
        mock_logger.error.assert_called_once()
        assert "啟動背景任務時發生錯誤" in str(mock_logger.error.call_args)
    
    @patch('src.services.scheduler_manager.logger')
    def test_stop_all_tasks_exception_handling(self, mock_logger):
        """測試停止背景任務的異常處理"""
        # 設定為運行狀態並模擬拋出異常
        self.scheduler_manager._is_running = True
        self.mock_scheduler.shutdown.side_effect = Exception("調度器停止錯誤")
        
        # 執行測試
        self.scheduler_manager.stop_all_tasks()
        
        # 驗證錯誤日誌記錄
        mock_logger.error.assert_called_once()
        assert "停止背景任務時發生錯誤" in str(mock_logger.error.call_args)
    
    @patch('src.services.scheduler_manager.logger')
    def test_get_job_status_exception_handling(self, mock_logger):
        """測試取得任務狀態的異常處理"""
        # 設定模擬拋出異常
        self.mock_scheduler.get_jobs.side_effect = Exception("取得任務錯誤")
        
        # 執行測試
        status = self.scheduler_manager.get_job_status()
        
        # 驗證回傳預設值並記錄錯誤
        assert status == {'is_running': False, 'jobs': {}}
        mock_logger.error.assert_called_once()
        assert "取得任務狀態時發生錯誤" in str(mock_logger.error.call_args)