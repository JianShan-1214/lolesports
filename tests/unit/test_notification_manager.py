"""
通知管理模組單元測試
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import uuid

from src.services.notification_manager import NotificationManager
from src.models.user import UserSubscription
from src.models.team import Team
from src.models.match import Match
from src.models.notification import NotificationRecord


class TestNotificationManager:
    """通知管理類別測試"""
    
    def setup_method(self):
        """設定測試環境"""
        # 建立模擬的依賴項目
        self.mock_data_manager = Mock()
        self.mock_telegram_api = Mock()
        
        # 建立通知管理器實例並注入模擬依賴
        self.notification_manager = NotificationManager()
        self.notification_manager.data_manager = self.mock_data_manager
        self.notification_manager.telegram_api = self.mock_telegram_api
        
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
            scheduled_time=datetime(2024, 1, 15, 18, 0),
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled",
            stream_url="https://twitch.tv/lck"
        )
        
        self.user_subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1", "Gen.G"]
        )
    
    def test_create_match_notification_with_stream_url(self):
        """測試建立包含直播連結的比賽通知訊息"""
        message = self.notification_manager.create_match_notification(self.match)
        
        assert "🎮 <b>LOL比賽提醒</b>" in message
        assert "<b>T1</b> vs <b>Gen.G</b>" in message
        assert "LCK Spring 2024" in message
        assert "2024年01月15日 18:00" in message
        assert "BO3" in message
        assert "https://twitch.tv/lck" in message
        assert "祝您觀賽愉快！ 🎉" in message
    
    def test_create_match_notification_without_stream_url(self):
        """測試建立不包含直播連結的比賽通知訊息"""
        match_without_stream = Match(
            match_id="match_002",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 18, 0),
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        message = self.notification_manager.create_match_notification(match_without_stream)
        
        assert "🎮 <b>LOL比賽提醒</b>" in message
        assert "<b>T1</b> vs <b>Gen.G</b>" in message
        assert "🔗" not in message  # 沒有直播連結
        assert "祝您觀賽愉快！ 🎉" in message
    
    def test_send_notifications_for_match_with_subscribers(self):
        """測試為有訂閱者的比賽發送通知"""
        # 設定模擬回傳值
        self.mock_data_manager.get_all_subscriptions.return_value = [self.user_subscription]
        self.mock_telegram_api.send_notification.return_value = True
        
        # 執行測試
        self.notification_manager.send_notifications_for_match(self.match)
        
        # 驗證呼叫
        self.mock_data_manager.get_all_subscriptions.assert_called_once()
        self.mock_telegram_api.send_notification.assert_called_once()
        self.mock_data_manager.save_notification_record.assert_called_once()
        
        # 驗證通知記錄的儲存
        saved_record = self.mock_data_manager.save_notification_record.call_args[0][0]
        assert saved_record.user_id == "123456789"
        assert saved_record.match_id == "match_001"
        assert saved_record.status == "sent"
    
    def test_send_notifications_for_match_no_subscribers(self):
        """測試為沒有訂閱者的比賽發送通知"""
        # 建立沒有相關訂閱者的比賽
        other_team1 = Team(team_id="drx", name="DRX", region="KR", league="LCK")
        other_team2 = Team(team_id="kt", name="KT", region="KR", league="LCK")
        other_match = Match(
            match_id="match_003",
            team1=other_team1,
            team2=other_team2,
            scheduled_time=datetime(2024, 1, 15, 18, 0),
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        # 設定模擬回傳值
        self.mock_data_manager.get_all_subscriptions.return_value = [self.user_subscription]
        
        # 執行測試
        self.notification_manager.send_notifications_for_match(other_match)
        
        # 驗證沒有發送通知
        self.mock_telegram_api.send_notification.assert_not_called()
        self.mock_data_manager.save_notification_record.assert_not_called()
    
    def test_send_notifications_telegram_api_failure(self):
        """測試Telegram API發送失敗的情況"""
        # 設定模擬回傳值
        self.mock_data_manager.get_all_subscriptions.return_value = [self.user_subscription]
        self.mock_telegram_api.send_notification.return_value = False
        
        # 執行測試
        self.notification_manager.send_notifications_for_match(self.match)
        
        # 驗證通知記錄標記為失敗
        saved_record = self.mock_data_manager.save_notification_record.call_args[0][0]
        assert saved_record.status == "failed"
        assert saved_record.error_message == "Telegram API發送失敗"
    
    @patch('src.services.notification_manager.uuid.uuid4')
    def test_send_notification_to_user_success(self, mock_uuid):
        """測試成功發送通知給特定使用者"""
        # 設定模擬UUID
        mock_uuid.return_value = MagicMock()
        mock_uuid.return_value.__str__ = Mock(return_value="test-uuid-123")
        
        # 設定模擬回傳值
        self.mock_telegram_api.send_notification.return_value = True
        
        # 建立測試訊息
        test_message = "測試通知訊息"
        
        # 執行測試
        self.notification_manager._send_notification_to_user(
            self.user_subscription, 
            self.match, 
            test_message
        )
        
        # 驗證Telegram API呼叫
        self.mock_telegram_api.send_notification.assert_called_once_with(
            "123456789", 
            test_message
        )
        
        # 驗證通知記錄儲存
        self.mock_data_manager.save_notification_record.assert_called_once()
        saved_record = self.mock_data_manager.save_notification_record.call_args[0][0]
        assert saved_record.notification_id == "test-uuid-123"
        assert saved_record.user_id == "123456789"
        assert saved_record.match_id == "match_001"
        assert saved_record.message == test_message
        assert saved_record.status == "sent"
    
    def test_get_subscribers_for_team(self):
        """測試取得特定戰隊的訂閱者"""
        # 建立多個訂閱者
        user1 = UserSubscription(
            user_id="111111111",
            telegram_username="user1",
            subscribed_teams=["T1", "DRX"]
        )
        
        user2 = UserSubscription(
            user_id="222222222",
            telegram_username="user2",
            subscribed_teams=["Gen.G", "KT"]
        )
        
        user3 = UserSubscription(
            user_id="333333333",
            telegram_username="user3",
            subscribed_teams=["T1", "Gen.G"]
        )
        
        # 設定模擬回傳值
        self.mock_data_manager.get_all_subscriptions.return_value = [user1, user2, user3]
        
        # 測試取得T1的訂閱者
        t1_subscribers = self.notification_manager.get_subscribers_for_team("T1")
        
        assert len(t1_subscribers) == 2
        assert user1 in t1_subscribers
        assert user3 in t1_subscribers
        assert user2 not in t1_subscribers
        
        # 測試取得不存在戰隊的訂閱者
        no_subscribers = self.notification_manager.get_subscribers_for_team("NonExistentTeam")
        assert len(no_subscribers) == 0
    
    def test_retry_failed_notifications(self):
        """測試重試失敗的通知"""
        # 建立失敗的通知記錄
        failed_record1 = NotificationRecord(
            notification_id="failed_001",
            user_id="123456789",
            match_id="match_001",
            message="測試訊息1",
            status="failed",
            retry_count=1,
            sent_at=datetime.now() - timedelta(hours=1)
        )
        
        failed_record2 = NotificationRecord(
            notification_id="failed_002",
            user_id="987654321",
            match_id="match_002",
            message="測試訊息2",
            status="failed",
            retry_count=2,
            sent_at=datetime.now() - timedelta(hours=2)
        )
        
        # 建立已達到最大重試次數的記錄
        max_retry_record = NotificationRecord(
            notification_id="failed_003",
            user_id="555555555",
            match_id="match_003",
            message="測試訊息3",
            status="failed",
            retry_count=3,
            sent_at=datetime.now() - timedelta(hours=1)
        )
        
        # 建立過舊的失敗記錄
        old_record = NotificationRecord(
            notification_id="failed_004",
            user_id="444444444",
            match_id="match_004",
            message="測試訊息4",
            status="failed",
            retry_count=1,
            sent_at=datetime.now() - timedelta(hours=25)  # 超過24小時
        )
        
        # 設定模擬回傳值
        self.mock_data_manager.get_notification_history.return_value = [
            failed_record1, failed_record2, max_retry_record, old_record
        ]
        self.mock_telegram_api.send_notification.return_value = True
        
        # 執行測試
        self.notification_manager.retry_failed_notifications()
        
        # 驗證只重試了符合條件的記錄（failed_record1 和 failed_record2）
        assert self.mock_telegram_api.send_notification.call_count == 2
        assert self.mock_data_manager.save_notification_record.call_count == 2
    
    def test_retry_failed_notifications_no_failed_records(self):
        """測試沒有失敗通知時的重試行為"""
        # 設定模擬回傳值：沒有失敗的記錄
        successful_record = NotificationRecord(
            notification_id="success_001",
            user_id="123456789",
            match_id="match_001",
            message="測試訊息",
            status="sent",
            retry_count=0,
            sent_at=datetime.now() - timedelta(hours=1)
        )
        
        self.mock_data_manager.get_notification_history.return_value = [successful_record]
        
        # 執行測試
        self.notification_manager.retry_failed_notifications()
        
        # 驗證沒有進行重試
        self.mock_telegram_api.send_notification.assert_not_called()
        self.mock_data_manager.save_notification_record.assert_not_called()
    
    def test_send_test_notification(self):
        """測試發送測試通知"""
        # 設定模擬回傳值
        self.mock_telegram_api.send_test_message.return_value = True
        
        # 執行測試
        result = self.notification_manager.send_test_notification("123456789")
        
        # 驗證結果
        assert result is True
        self.mock_telegram_api.send_test_message.assert_called_once_with("123456789")
    
    def test_send_test_notification_failure(self):
        """測試發送測試通知失敗"""
        # 設定模擬回傳值
        self.mock_telegram_api.send_test_message.return_value = False
        
        # 執行測試
        result = self.notification_manager.send_test_notification("123456789")
        
        # 驗證結果
        assert result is False
        self.mock_telegram_api.send_test_message.assert_called_once_with("123456789")
    
    @patch('src.services.notification_manager.logger')
    def test_send_notifications_exception_handling(self, mock_logger):
        """測試發送通知時的異常處理"""
        # 設定模擬拋出異常
        self.mock_data_manager.get_all_subscriptions.side_effect = Exception("資料庫錯誤")
        
        # 執行測試
        self.notification_manager.send_notifications_for_match(self.match)
        
        # 驗證錯誤日誌記錄
        mock_logger.error.assert_called_once()
        assert "發送比賽通知時發生錯誤" in str(mock_logger.error.call_args)
    
    @patch('src.services.notification_manager.logger')
    def test_get_subscribers_exception_handling(self, mock_logger):
        """測試取得訂閱者時的異常處理"""
        # 設定模擬拋出異常
        self.mock_data_manager.get_all_subscriptions.side_effect = Exception("資料庫錯誤")
        
        # 執行測試
        result = self.notification_manager.get_subscribers_for_team("T1")
        
        # 驗證回傳空列表並記錄錯誤
        assert result == []
        mock_logger.error.assert_called_once()
        assert "取得戰隊 T1 訂閱者時發生錯誤" in str(mock_logger.error.call_args)
    
    @patch('src.services.notification_manager.logger')
    def test_retry_failed_notifications_exception_handling(self, mock_logger):
        """測試重試失敗通知時的異常處理"""
        # 設定模擬拋出異常
        self.mock_data_manager.get_notification_history.side_effect = Exception("資料庫錯誤")
        
        # 執行測試
        self.notification_manager.retry_failed_notifications()
        
        # 驗證錯誤日誌記錄
        mock_logger.error.assert_called_once()
        assert "重試失敗通知時發生錯誤" in str(mock_logger.error.call_args)