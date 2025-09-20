"""
端到端整合測試
測試從用戶訂閱到通知發送的完整流程
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time

from src.services.data_manager import DataManager
from src.services.leaguepedia_api import LeaguepediaAPI
from src.services.telegram_api import TelegramAPI
from src.services.notification_manager import NotificationManager
from src.services.scheduler_manager import SchedulerManager
from src.models.user import UserSubscription
from src.models.team import Team
from src.models.match import Match

from tests.fixtures.test_data import IntegrationTestHelper


class TestEndToEndFlow:
    """端到端流程測試類別"""
    
    def setup_method(self):
        """設定測試環境"""
        IntegrationTestHelper.setup_test_environment()
        
        # 建立服務實例（這會自動初始化資料庫）
        self.data_manager = DataManager()
        self.leaguepedia_api = LeaguepediaAPI()
        self.telegram_api = TelegramAPI()
        self.notification_manager = NotificationManager()
        self.scheduler_manager = SchedulerManager()
    
    def teardown_method(self):
        """清理測試環境"""
        IntegrationTestHelper.cleanup_test_environment()
    
    @patch('src.services.telegram_api.TelegramAPI.send_notification')
    @patch('src.services.leaguepedia_api.LeaguepediaAPI.get_upcoming_matches')
    def test_complete_user_subscription_to_notification_flow(
        self, 
        mock_get_matches, 
        mock_send_notification,
        temp_database,
        test_teams,
        test_matches
    ):
        """測試完整的用戶訂閱到通知發送流程"""
        
        # 1. 模擬API回應
        mock_get_matches.return_value = test_matches[:2]  # 返回前兩個比賽
        mock_send_notification.return_value = True
        
        # 2. 用戶建立訂閱
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="integration_test_user",
            subscribed_teams=["T1", "Gen.G"]
        )
        
        # 儲存訂閱
        save_result = self.data_manager.save_subscription(subscription)
        assert save_result is True
        
        # 驗證訂閱已儲存
        retrieved_subscription = self.data_manager.get_user_subscription("123456789")
        assert retrieved_subscription is not None
        assert retrieved_subscription.user_id == "123456789"
        assert "T1" in retrieved_subscription.subscribed_teams
        assert "Gen.G" in retrieved_subscription.subscribed_teams
        
        # 3. 系統獲取比賽資料
        upcoming_matches = self.leaguepedia_api.get_upcoming_matches(days=2)
        assert len(upcoming_matches) == 2
        
        # 清空現有快取並重新快取測試資料
        try:
            import sqlite3
            with sqlite3.connect(temp_database) as conn:
                cursor = conn.cursor()
                # 檢查表是否存在，如果存在則清空
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='matches'")
                if cursor.fetchone():
                    cursor.execute("DELETE FROM matches")
                    conn.commit()
        except Exception as e:
            print(f"清空快取時發生錯誤: {e}")
        
        # 快取比賽資料
        cache_result = self.data_manager.cache_match_data(upcoming_matches)
        assert cache_result is True
        
        # 驗證比賽資料已快取（允許有其他資料存在）
        cached_matches = self.data_manager.get_cached_matches()
        assert len(cached_matches) >= 2  # 至少有我們剛快取的2個比賽
        
        # 4. 檢查即將開始的比賽並發送通知
        # 使用我們剛快取的測試比賽資料
        test_match = upcoming_matches[0]  # 使用第一個測試比賽
        if test_match.has_team("T1"):
            # 發送通知
            self.notification_manager.send_notifications_for_match(test_match)
            
            # 驗證通知發送被調用
            mock_send_notification.assert_called()
            
            # 檢查通知記錄
            notification_history = self.data_manager.get_notification_history(limit=10)
            assert len(notification_history) > 0
            
            # 驗證通知記錄內容
            notification = notification_history[0]
            assert notification.user_id == "123456789"
            assert notification.match_id == test_match.match_id
            assert notification.status == "sent"
        
        print("✅ 完整流程測試通過：用戶訂閱 → 比賽資料獲取 → 通知發送")
    
    @patch('src.services.telegram_api.TelegramAPI.send_notification')
    @patch('src.services.leaguepedia_api.LeaguepediaAPI.get_upcoming_matches')
    def test_multiple_users_notification_flow(
        self, 
        mock_get_matches, 
        mock_send_notification,
        temp_database,
        test_teams,
        test_matches,
        test_subscriptions
    ):
        """測試多用戶通知流程"""
        
        # 模擬API回應
        mock_get_matches.return_value = [test_matches[0]]  # T1 vs Gen.G
        mock_send_notification.return_value = True
        
        # 儲存多個用戶訂閱
        for subscription in test_subscriptions:
            save_result = self.data_manager.save_subscription(subscription)
            assert save_result is True
        
        # 獲取並快取比賽資料
        upcoming_matches = self.leaguepedia_api.get_upcoming_matches(days=1)
        self.data_manager.cache_match_data(upcoming_matches)
        
        # 發送通知給相關用戶
        match = upcoming_matches[0]  # T1 vs Gen.G
        self.notification_manager.send_notifications_for_match(match)
        
        # 驗證通知發送次數
        # 應該有3個用戶收到通知（訂閱了T1或Gen.G的用戶）
        expected_notifications = 0
        for subscription in test_subscriptions:
            if "T1" in subscription.subscribed_teams or "Gen.G" in subscription.subscribed_teams:
                expected_notifications += 1
        
        assert mock_send_notification.call_count == expected_notifications
        
        # 驗證通知記錄
        notification_history = self.data_manager.get_notification_history(limit=10)
        assert len(notification_history) == expected_notifications
        
        print(f"✅ 多用戶通知測試通過：{expected_notifications} 個用戶收到通知")
    
    @patch('src.services.telegram_api.TelegramAPI.send_notification')
    @patch('src.services.leaguepedia_api.LeaguepediaAPI.get_upcoming_matches')
    def test_notification_retry_mechanism(
        self, 
        mock_get_matches, 
        mock_send_notification,
        temp_database,
        test_teams,
        test_matches
    ):
        """測試通知重試機制"""
        
        # 模擬第一次發送失敗，第二次成功
        mock_get_matches.return_value = [test_matches[0]]
        mock_send_notification.side_effect = [False, True]  # 第一次失敗，第二次成功
        
        # 建立訂閱
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="retry_test_user",
            subscribed_teams=["T1"]
        )
        self.data_manager.save_subscription(subscription)
        
        # 獲取比賽資料
        upcoming_matches = self.leaguepedia_api.get_upcoming_matches(days=1)
        self.data_manager.cache_match_data(upcoming_matches)
        
        # 第一次發送通知（會失敗）
        match = upcoming_matches[0]
        self.notification_manager.send_notifications_for_match(match)
        
        # 檢查失敗的通知記錄
        notification_history = self.data_manager.get_notification_history(limit=1)
        assert len(notification_history) == 1
        failed_notification = notification_history[0]
        assert failed_notification.status == "failed"
        assert failed_notification.can_retry() is True
        
        # 執行重試機制
        self.notification_manager.retry_failed_notifications()
        
        # 驗證重試後的狀態
        updated_history = self.data_manager.get_notification_history(limit=1)
        retried_notification = updated_history[0]
        assert retried_notification.status == "sent"
        assert retried_notification.retry_count == 1
        
        print("✅ 通知重試機制測試通過")
    
    @patch('src.services.telegram_api.TelegramAPI.validate_bot_token')
    @patch('src.services.leaguepedia_api.LeaguepediaAPI.get_team_list')
    def test_system_initialization_flow(
        self, 
        mock_get_teams, 
        mock_validate_token,
        temp_database,
        test_teams
    ):
        """測試系統初始化流程"""
        
        # 模擬API回應
        mock_validate_token.return_value = True
        mock_get_teams.return_value = test_teams
        
        # 1. 驗證Telegram Bot Token
        token_valid = self.telegram_api.validate_bot_token()
        assert token_valid is True
        
        # 2. 獲取戰隊列表
        teams = self.leaguepedia_api.get_team_list()
        assert len(teams) == len(test_teams)
        assert teams[0].name == "T1"
        
        # 3. 初始化資料庫
        # 資料庫應該在DataManager初始化時自動建立
        assert self.data_manager is not None
        
        # 4. 測試基本功能
        test_subscription = UserSubscription(
            user_id="999888777",
            telegram_username="init_test_user",
            subscribed_teams=["T1"]
        )
        
        save_result = self.data_manager.save_subscription(test_subscription)
        assert save_result is True
        
        retrieved = self.data_manager.get_user_subscription("999888777")
        assert retrieved is not None
        
        print("✅ 系統初始化流程測試通過")
    
    @patch('src.services.telegram_api.TelegramAPI.send_notification')
    @patch('src.services.leaguepedia_api.LeaguepediaAPI.get_upcoming_matches')
    def test_subscription_management_flow(
        self, 
        mock_get_matches, 
        mock_send_notification,
        temp_database,
        test_teams,
        test_matches
    ):
        """測試訂閱管理流程"""
        
        mock_get_matches.return_value = test_matches[:2]
        mock_send_notification.return_value = True
        
        # 1. 建立初始訂閱
        subscription = UserSubscription(
            user_id="555444333",
            telegram_username="management_test_user",
            subscribed_teams=["T1"]
        )
        self.data_manager.save_subscription(subscription)
        
        # 2. 更新訂閱（新增戰隊）
        updated_subscription = UserSubscription(
            user_id="555444333",
            telegram_username="management_test_user",
            subscribed_teams=["T1", "Gen.G", "DRX"]
        )
        update_result = self.data_manager.save_subscription(updated_subscription)
        assert update_result is True
        
        # 驗證更新
        retrieved = self.data_manager.get_user_subscription("555444333")
        assert len(retrieved.subscribed_teams) == 3
        assert "Gen.G" in retrieved.subscribed_teams
        assert "DRX" in retrieved.subscribed_teams
        
        # 3. 測試更新後的通知
        upcoming_matches = self.leaguepedia_api.get_upcoming_matches(days=2)
        self.data_manager.cache_match_data(upcoming_matches)
        
        # 發送通知
        for match in upcoming_matches:
            if match.has_team("Gen.G"):
                self.notification_manager.send_notifications_for_match(match)
                break
        
        # 驗證用戶收到Gen.G的比賽通知
        notification_history = self.data_manager.get_notification_history(limit=5)
        gen_g_notifications = [
            n for n in notification_history 
            if n.user_id == "555444333" and "Gen.G" in n.message
        ]
        assert len(gen_g_notifications) > 0
        
        # 4. 刪除訂閱
        delete_result = self.data_manager.delete_subscription("555444333")
        assert delete_result is True
        
        # 驗證刪除
        deleted_subscription = self.data_manager.get_user_subscription("555444333")
        assert deleted_subscription is None
        
        print("✅ 訂閱管理流程測試通過")
    
    def test_data_persistence_across_restarts(self, temp_database, test_subscriptions):
        """測試資料在系統重啟後的持久性"""
        
        # 1. 儲存資料
        for subscription in test_subscriptions:
            save_result = self.data_manager.save_subscription(subscription)
            assert save_result is True
        
        # 2. 模擬系統重啟（重新建立DataManager實例）
        new_data_manager = DataManager()
        
        # 3. 驗證資料仍然存在
        all_subscriptions = new_data_manager.get_all_subscriptions()
        assert len(all_subscriptions) == len(test_subscriptions)
        
        # 驗證特定訂閱
        test_user = new_data_manager.get_user_subscription("123456789")
        assert test_user is not None
        assert test_user.telegram_username == "test_user_1"
        assert "T1" in test_user.subscribed_teams
        
        print("✅ 資料持久性測試通過")
    
    @patch('src.services.telegram_api.TelegramAPI.send_notification')
    def test_notification_message_formatting(
        self, 
        mock_send_notification,
        temp_database,
        test_teams,
        test_matches
    ):
        """測試通知訊息格式化"""
        
        mock_send_notification.return_value = True
        
        # 建立訂閱
        subscription = UserSubscription(
            user_id="777888999",
            telegram_username="format_test_user",
            subscribed_teams=["T1"]
        )
        self.data_manager.save_subscription(subscription)
        
        # 測試通知訊息格式
        match = test_matches[0]  # T1 vs Gen.G
        message = self.notification_manager.create_match_notification(match)
        
        # 驗證訊息內容
        assert "T1" in message
        assert "Gen.G" in message
        assert "LCK Spring 2025" in message
        assert "BO3" in message
        assert "🎮" in message  # 確保有表情符號
        
        # 發送通知並檢查調用參數
        self.notification_manager.send_notifications_for_match(match)
        
        # 驗證send_notification被正確調用
        mock_send_notification.assert_called()
        call_args = mock_send_notification.call_args
        sent_message = call_args[0][1]  # 第二個參數是訊息內容
        
        assert "T1" in sent_message
        assert "Gen.G" in sent_message
        
        print("✅ 通知訊息格式化測試通過")