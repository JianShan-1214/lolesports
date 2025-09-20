"""
資料管理模組單元測試
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from src.services.data_manager import DataManager
from src.models.user import UserSubscription
from src.models.team import Team
from src.models.match import Match
from src.models.notification import NotificationRecord


class TestDataManager:
    """資料管理模組測試"""
    
    def setup_method(self):
        """設定測試環境"""
        # 建立臨時資料庫檔案
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 修改設定以使用臨時資料庫
        from config.settings import settings
        self.original_db_path = settings._config['database']['path']
        settings._config['database']['path'] = self.temp_db.name
        
        # 建立資料管理器實例
        self.data_manager = DataManager()
        
        # 建立測試資料
        self.test_subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1", "Gen.G"]
        )
        
        self.test_team1 = Team(
            team_id="t1",
            name="T1",
            region="KR",
            league="LCK"
        )
        
        self.test_team2 = Team(
            team_id="geng",
            name="Gen.G",
            region="KR",
            league="LCK"
        )
        
        self.test_match = Match(
            match_id="match_001",
            team1=self.test_team1,
            team2=self.test_team2,
            scheduled_time=datetime(2025, 12, 15, 18, 0),
            tournament="LCK Spring 2025",
            match_format="BO3",
            status="scheduled"
        )
        
        self.test_notification = NotificationRecord(
            notification_id="notif_001",
            user_id="123456789",
            match_id="match_001",
            message="T1 vs Gen.G 比賽即將開始！"
        )
    
    def teardown_method(self):
        """清理測試環境"""
        # 恢復原始設定
        from config.settings import settings
        settings._config['database']['path'] = self.original_db_path
        
        # 刪除臨時資料庫檔案
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_init_database(self):
        """測試資料庫初始化"""
        # 資料庫檔案應該存在
        assert Path(self.temp_db.name).exists()
        
        # 檢查資料表是否建立
        import sqlite3
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # 檢查使用者訂閱表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_subscriptions'")
            assert cursor.fetchone() is not None
            
            # 檢查比賽資料表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='matches'")
            assert cursor.fetchone() is not None
            
            # 檢查通知記錄表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notification_records'")
            assert cursor.fetchone() is not None
    
    def test_save_and_get_subscription(self):
        """測試儲存和取得訂閱"""
        # 儲存訂閱
        result = self.data_manager.save_subscription(self.test_subscription)
        assert result is True
        
        # 取得訂閱
        retrieved = self.data_manager.get_user_subscription("123456789")
        assert retrieved is not None
        assert retrieved.user_id == "123456789"
        assert retrieved.telegram_username == "test_user"
        assert retrieved.subscribed_teams == ["T1", "Gen.G"]
        assert retrieved.is_active is True
    
    def test_get_nonexistent_subscription(self):
        """測試取得不存在的訂閱"""
        result = self.data_manager.get_user_subscription("nonexistent")
        assert result is None
    
    def test_get_all_subscriptions(self):
        """測試取得所有訂閱"""
        # 儲存多個訂閱
        subscription1 = UserSubscription(
            user_id="111111111",
            telegram_username="user1",
            subscribed_teams=["T1"]
        )
        
        subscription2 = UserSubscription(
            user_id="222222222",
            telegram_username="user2",
            subscribed_teams=["Gen.G"]
        )
        
        self.data_manager.save_subscription(subscription1)
        self.data_manager.save_subscription(subscription2)
        
        # 取得所有訂閱
        all_subscriptions = self.data_manager.get_all_subscriptions()
        assert len(all_subscriptions) == 2
        
        user_ids = [sub.user_id for sub in all_subscriptions]
        assert "111111111" in user_ids
        assert "222222222" in user_ids
    
    def test_delete_subscription(self):
        """測試刪除訂閱"""
        # 先儲存訂閱
        self.data_manager.save_subscription(self.test_subscription)
        
        # 確認訂閱存在
        retrieved = self.data_manager.get_user_subscription("123456789")
        assert retrieved is not None
        
        # 刪除訂閱
        result = self.data_manager.delete_subscription("123456789")
        assert result is True
        
        # 確認訂閱不在活躍列表中
        all_subscriptions = self.data_manager.get_all_subscriptions()
        user_ids = [sub.user_id for sub in all_subscriptions]
        assert "123456789" not in user_ids
    
    def test_cache_and_get_matches(self):
        """測試快取和取得比賽資料"""
        # 快取比賽資料
        matches = [self.test_match]
        result = self.data_manager.cache_match_data(matches)
        assert result is True
        
        # 取得快取的比賽資料
        cached_matches = self.data_manager.get_cached_matches()
        assert len(cached_matches) == 1
        
        match = cached_matches[0]
        assert match.match_id == "match_001"
        assert match.team1.name == "T1"
        assert match.team2.name == "Gen.G"
        assert match.tournament == "LCK Spring 2025"
    
    def test_cache_multiple_matches(self):
        """測試快取多個比賽資料"""
        # 建立第二個比賽
        match2 = Match(
            match_id="match_002",
            team1=self.test_team2,
            team2=self.test_team1,
            scheduled_time=datetime(2025, 12, 16, 18, 0),
            tournament="LCK Spring 2025",
            match_format="BO1",
            status="scheduled"
        )
        
        # 快取多個比賽
        matches = [self.test_match, match2]
        result = self.data_manager.cache_match_data(matches)
        assert result is True
        
        # 取得快取的比賽資料
        cached_matches = self.data_manager.get_cached_matches()
        assert len(cached_matches) == 2
        
        match_ids = [match.match_id for match in cached_matches]
        assert "match_001" in match_ids
        assert "match_002" in match_ids
    
    def test_save_notification_record(self):
        """測試儲存通知記錄"""
        result = self.data_manager.save_notification_record(self.test_notification)
        assert result is True
        
        # 驗證記錄已儲存
        history = self.data_manager.get_notification_history(limit=1)
        assert len(history) == 1
        
        record = history[0]
        assert record.notification_id == "notif_001"
        assert record.user_id == "123456789"
        assert record.match_id == "match_001"
        assert record.message == "T1 vs Gen.G 比賽即將開始！"
        assert record.status == "pending"
    
    def test_get_notification_history(self):
        """測試取得通知歷史"""
        # 儲存多個通知記錄
        notification1 = NotificationRecord(
            notification_id="notif_001",
            user_id="123456789",
            match_id="match_001",
            message="通知1"
        )
        
        notification2 = NotificationRecord(
            notification_id="notif_002",
            user_id="123456789",
            match_id="match_002",
            message="通知2"
        )
        
        self.data_manager.save_notification_record(notification1)
        self.data_manager.save_notification_record(notification2)
        
        # 取得歷史記錄
        history = self.data_manager.get_notification_history(limit=10)
        assert len(history) == 2
        
        # 檢查記錄順序（應該按時間倒序）
        notification_ids = [record.notification_id for record in history]
        assert "notif_002" in notification_ids
        assert "notif_001" in notification_ids
    
    def test_get_notification_history_with_limit(self):
        """測試限制通知歷史數量"""
        # 儲存多個通知記錄
        for i in range(5):
            notification = NotificationRecord(
                notification_id=f"notif_{i:03d}",
                user_id="123456789",
                match_id="match_001",
                message=f"通知{i}"
            )
            self.data_manager.save_notification_record(notification)
        
        # 限制取得數量
        history = self.data_manager.get_notification_history(limit=3)
        assert len(history) == 3
    
    def test_update_existing_subscription(self):
        """測試更新現有訂閱"""
        # 儲存初始訂閱
        self.data_manager.save_subscription(self.test_subscription)
        
        # 修改訂閱
        updated_subscription = UserSubscription(
            user_id="123456789",
            telegram_username="updated_user",
            subscribed_teams=["T1", "Gen.G", "DRX"]
        )
        
        # 更新訂閱
        result = self.data_manager.save_subscription(updated_subscription)
        assert result is True
        
        # 驗證更新
        retrieved = self.data_manager.get_user_subscription("123456789")
        assert retrieved.telegram_username == "updated_user"
        assert len(retrieved.subscribed_teams) == 3
        assert "DRX" in retrieved.subscribed_teams
    
    def test_update_existing_match(self):
        """測試更新現有比賽"""
        # 快取初始比賽
        self.data_manager.cache_match_data([self.test_match])
        
        # 修改比賽狀態
        updated_match = Match(
            match_id="match_001",
            team1=self.test_team1,
            team2=self.test_team2,
            scheduled_time=datetime(2025, 12, 15, 18, 0),
            tournament="LCK Spring 2025",
            match_format="BO3",
            status="live"  # 狀態改為進行中
        )
        
        # 更新比賽
        result = self.data_manager.cache_match_data([updated_match])
        assert result is True
        
        # 驗證更新
        cached_matches = self.data_manager.get_cached_matches()
        assert len(cached_matches) == 1
        assert cached_matches[0].status == "live"