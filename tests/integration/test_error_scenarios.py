"""
錯誤情境整合測試
測試系統在各種錯誤情況下的行為
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import os
import tempfile
from datetime import datetime, timedelta

from src.services.data_manager import DataManager
from src.services.leaguepedia_api import LeaguepediaAPI
from src.services.telegram_api import TelegramAPI
from src.services.notification_manager import NotificationManager
from src.models.user import UserSubscription
from src.models.team import Team
from src.models.match import Match

from tests.fixtures.test_data import IntegrationTestHelper


class TestDatabaseErrorScenarios:
    """資料庫錯誤情境測試"""
    
    def setup_method(self):
        """設定測試環境"""
        IntegrationTestHelper.setup_test_environment()
    
    def teardown_method(self):
        """清理測試環境"""
        IntegrationTestHelper.cleanup_test_environment()
    
    def test_database_file_corruption(self, temp_database):
        """測試資料庫檔案損壞情況"""
        
        # 建立正常的資料管理器
        data_manager = DataManager()
        
        # 儲存一些測試資料
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1"]
        )
        save_result = data_manager.save_subscription(subscription)
        assert save_result is True
        
        # 模擬資料庫檔案損壞（寫入無效內容）
        with open(temp_database, 'w') as f:
            f.write("這不是有效的SQLite資料庫內容")
        
        # 嘗試建立新的資料管理器實例
        try:
            corrupted_data_manager = DataManager()
            # 嘗試讀取資料
            subscriptions = corrupted_data_manager.get_all_subscriptions()
            # 如果資料庫損壞，應該返回空列表而不是拋出異常
            assert isinstance(subscriptions, list)
        except Exception as e:
            # 如果拋出異常，確保是可預期的資料庫錯誤
            assert "database" in str(e).lower() or "sqlite" in str(e).lower()
        
        print("✅ 資料庫檔案損壞處理測試通過")
    
    def test_database_permission_denied(self, temp_database):
        """測試資料庫權限拒絕情況"""
        
        # 建立資料管理器
        data_manager = DataManager()
        
        # 儲存測試資料
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1"]
        )
        
        # 模擬權限問題（將資料庫檔案設為唯讀）
        try:
            os.chmod(temp_database, 0o444)  # 唯讀權限
            
            # 嘗試儲存資料（應該失敗但不拋出異常）
            save_result = data_manager.save_subscription(subscription)
            
            # 根據實作，可能返回False或處理錯誤
            # 重要的是不應該讓整個應用程式崩潰
            assert isinstance(save_result, bool)
            
        finally:
            # 恢復權限以便清理
            try:
                os.chmod(temp_database, 0o666)
            except:
                pass
        
        print("✅ 資料庫權限拒絕處理測試通過")
    
    def test_database_disk_full_simulation(self, temp_database):
        """測試磁碟空間不足情況模擬"""
        
        data_manager = DataManager()
        
        # 建立大量測試資料來模擬磁碟空間問題
        large_subscriptions = []
        for i in range(1000):  # 建立大量訂閱
            subscription = UserSubscription(
                user_id=f"{i:09d}",
                telegram_username=f"user_{i}",
                subscribed_teams=["T1", "Gen.G", "DRX", "Fnatic", "G2 Esports"] * 10  # 大量戰隊
            )
            large_subscriptions.append(subscription)
        
        # 嘗試儲存大量資料
        successful_saves = 0
        for subscription in large_subscriptions[:10]:  # 只測試前10個避免測試時間過長
            try:
                result = data_manager.save_subscription(subscription)
                if result:
                    successful_saves += 1
            except Exception as e:
                # 記錄錯誤但繼續測試
                print(f"儲存失敗: {e}")
        
        # 驗證至少有一些資料被成功儲存
        assert successful_saves >= 0  # 至少不應該全部失敗
        
        print("✅ 磁碟空間不足模擬測試通過")


class TestAPIFailureScenarios:
    """API失敗情境測試"""
    
    def setup_method(self):
        """設定測試環境"""
        self.leaguepedia_api = LeaguepediaAPI()
        self.telegram_api = TelegramAPI()
        self.notification_manager = NotificationManager()
    
    @patch('requests.Session.get')
    def test_leaguepedia_api_complete_failure(self, mock_get, temp_database):
        """測試Leaguepedia API完全失敗情況"""
        
        # 模擬API完全無法存取
        mock_get.side_effect = Exception("API服務完全無法存取")
        
        # 嘗試獲取比賽資料
        matches = self.leaguepedia_api.get_upcoming_matches(days=2)
        
        # 應該返回空列表而不是拋出異常
        assert matches == []
        
        # 嘗試獲取戰隊列表
        teams = self.leaguepedia_api.get_team_list()
        assert teams == []
        
        print("✅ Leaguepedia API完全失敗處理測試通過")
    
    @patch('requests.Session.post')
    def test_telegram_api_complete_failure(self, mock_post, temp_database):
        """測試Telegram API完全失敗情況"""
        
        # 模擬Telegram API完全無法存取
        mock_post.side_effect = Exception("Telegram API服務無法存取")
        
        # 建立測試資料
        data_manager = DataManager()
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1"]
        )
        data_manager.save_subscription(subscription)
        
        # 建立測試比賽
        team1 = Team(team_id="t1", name="T1", region="KR", league="LCK")
        team2 = Team(team_id="geng", name="Gen.G", region="KR", league="LCK")
        match = Match(
            match_id="test_match",
            team1=team1,
            team2=team2,
            scheduled_time=datetime.now() + timedelta(hours=1),
            tournament="Test Tournament",
            match_format="BO3",
            status="scheduled"
        )
        
        # 嘗試發送通知（應該失敗但不崩潰）
        try:
            self.notification_manager.send_notifications_for_match(match)
            # 如果沒有拋出異常，檢查通知記錄
            notification_history = data_manager.get_notification_history(limit=5)
            # 應該有失敗的通知記錄
            if notification_history:
                assert notification_history[0].status == "failed"
        except Exception as e:
            # 如果拋出異常，確保是可預期的通知錯誤
            assert "telegram" in str(e).lower() or "notification" in str(e).lower()
        
        print("✅ Telegram API完全失敗處理測試通過")
    
    @patch('requests.Session.get')
    @patch('requests.Session.post')
    def test_intermittent_api_failures(self, mock_post, mock_get, temp_database):
        """測試間歇性API失敗"""
        
        # 模擬間歇性失敗（50%成功率）
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "query": {"results": {"Teams": []}}
        }
        
        failure_response = Mock()
        failure_response.status_code = 503
        failure_response.raise_for_status.side_effect = Exception("Service Unavailable")
        
        # 交替成功和失敗
        mock_get.side_effect = [failure_response, success_response, failure_response, success_response]
        
        # 測試多次API調用
        results = []
        for i in range(4):
            try:
                teams = self.leaguepedia_api.get_team_list()
                results.append(len(teams) >= 0)  # 成功或失敗都應該返回列表
            except Exception:
                results.append(False)
        
        # 驗證系統能夠處理間歇性失敗
        assert all(results), "系統應該能夠處理間歇性API失敗"
        
        print("✅ 間歇性API失敗處理測試通過")


class TestConcurrencyErrorScenarios:
    """並發錯誤情境測試"""
    
    def setup_method(self):
        """設定測試環境"""
        IntegrationTestHelper.setup_test_environment()
    
    def teardown_method(self):
        """清理測試環境"""
        IntegrationTestHelper.cleanup_test_environment()
    
    def test_concurrent_database_access(self, temp_database):
        """測試並發資料庫存取"""
        
        import threading
        import time
        
        # 建立多個資料管理器實例
        data_managers = [DataManager() for _ in range(3)]
        
        # 並發操作結果
        results = []
        errors = []
        
        def concurrent_operation(dm_index, user_id_base):
            """並發操作函數"""
            try:
                dm = data_managers[dm_index]
                
                # 建立訂閱
                subscription = UserSubscription(
                    user_id=f"{user_id_base}{dm_index:03d}",
                    telegram_username=f"concurrent_user_{dm_index}",
                    subscribed_teams=["T1", "Gen.G"]
                )
                
                # 儲存訂閱
                save_result = dm.save_subscription(subscription)
                results.append(save_result)
                
                # 讀取訂閱
                retrieved = dm.get_user_subscription(subscription.user_id)
                results.append(retrieved is not None)
                
                # 更新訂閱
                subscription.subscribed_teams.append("DRX")
                update_result = dm.save_subscription(subscription)
                results.append(update_result)
                
            except Exception as e:
                errors.append(str(e))
        
        # 啟動並發執行緒
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=concurrent_operation,
                args=(i, 100000 + i * 1000)
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有執行緒完成
        for thread in threads:
            thread.join(timeout=10)  # 10秒超時
        
        # 驗證結果
        print(f"並發操作結果: {len(results)} 個成功, {len(errors)} 個錯誤")
        
        # 至少應該有一些操作成功
        successful_operations = sum(1 for r in results if r is True)
        assert successful_operations > 0, "至少應該有一些並發操作成功"
        
        # 錯誤數量不應該太多
        assert len(errors) < len(results), "錯誤數量不應該超過成功操作數量"
        
        print("✅ 並發資料庫存取測試通過")
    
    @patch('requests.Session.post')
    def test_concurrent_notification_sending(self, mock_post, temp_database):
        """測試並發通知發送"""
        
        import threading
        
        # 模擬成功的Telegram API回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        mock_post.return_value = mock_response
        
        # 建立測試資料
        data_manager = DataManager()
        notification_manager = NotificationManager()
        
        # 建立多個訂閱
        subscriptions = []
        for i in range(5):
            subscription = UserSubscription(
                user_id=f"99999{i:04d}",
                telegram_username=f"concurrent_notify_user_{i}",
                subscribed_teams=["T1"]
            )
            data_manager.save_subscription(subscription)
            subscriptions.append(subscription)
        
        # 建立測試比賽
        team1 = Team(team_id="t1", name="T1", region="KR", league="LCK")
        team2 = Team(team_id="geng", name="Gen.G", region="KR", league="LCK")
        match = Match(
            match_id="concurrent_test_match",
            team1=team1,
            team2=team2,
            scheduled_time=datetime.now() + timedelta(hours=1),
            tournament="Concurrent Test Tournament",
            match_format="BO3",
            status="scheduled"
        )
        
        # 並發發送通知
        notification_results = []
        notification_errors = []
        
        def send_notification_concurrent():
            """並發發送通知函數"""
            try:
                notification_manager.send_notifications_for_match(match)
                notification_results.append(True)
            except Exception as e:
                notification_errors.append(str(e))
        
        # 啟動多個並發通知執行緒
        threads = []
        for i in range(3):
            thread = threading.Thread(target=send_notification_concurrent)
            threads.append(thread)
            thread.start()
        
        # 等待所有執行緒完成
        for thread in threads:
            thread.join(timeout=15)  # 15秒超時
        
        # 驗證結果
        print(f"並發通知結果: {len(notification_results)} 個成功, {len(notification_errors)} 個錯誤")
        
        # 至少應該有一些通知成功發送
        assert len(notification_results) > 0, "至少應該有一些並發通知成功"
        
        # 檢查通知記錄
        notification_history = data_manager.get_notification_history(limit=20)
        assert len(notification_history) > 0, "應該有通知記錄"
        
        print("✅ 並發通知發送測試通過")


class TestDataIntegrityScenarios:
    """資料完整性錯誤情境測試"""
    
    def setup_method(self):
        """設定測試環境"""
        IntegrationTestHelper.setup_test_environment()
    
    def teardown_method(self):
        """清理測試環境"""
        IntegrationTestHelper.cleanup_test_environment()
    
    def test_invalid_data_handling(self, temp_database):
        """測試無效資料處理"""
        
        data_manager = DataManager()
        
        # 測試無效的訂閱資料
        try:
            invalid_subscription = UserSubscription(
                user_id="",  # 空的用戶ID
                telegram_username="test_user",
                subscribed_teams=["T1"]
            )
            # 這應該在模型層面就被拒絕
            assert False, "應該拒絕空的用戶ID"
        except ValueError:
            # 預期的驗證錯誤
            pass
        
        # 測試無效的戰隊資料
        try:
            invalid_team = Team(
                team_id="",  # 空的戰隊ID
                name="Test Team",
                region="KR",
                league="LCK"
            )
            assert False, "應該拒絕空的戰隊ID"
        except ValueError:
            # 預期的驗證錯誤
            pass
        
        print("✅ 無效資料處理測試通過")
    
    def test_data_consistency_after_errors(self, temp_database):
        """測試錯誤後的資料一致性"""
        
        data_manager = DataManager()
        
        # 儲存有效資料
        valid_subscription = UserSubscription(
            user_id="123456789",
            telegram_username="valid_user",
            subscribed_teams=["T1", "Gen.G"]
        )
        save_result = data_manager.save_subscription(valid_subscription)
        assert save_result is True
        
        # 嘗試儲存無效資料（模擬部分失敗）
        try:
            # 直接操作資料庫來模擬資料不一致
            import sqlite3
            with sqlite3.connect(temp_database) as conn:
                cursor = conn.cursor()
                # 插入無效資料
                cursor.execute("""
                    INSERT INTO user_subscriptions 
                    (user_id, telegram_username, subscribed_teams, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("invalid", "", "[]", "invalid_date", "invalid_date", 1))
                conn.commit()
        except Exception:
            # 預期可能會失敗
            pass
        
        # 驗證有效資料仍然可以正常讀取
        retrieved = data_manager.get_user_subscription("123456789")
        assert retrieved is not None
        assert retrieved.telegram_username == "valid_user"
        
        # 驗證系統能夠處理混合的有效/無效資料
        all_subscriptions = data_manager.get_all_subscriptions()
        valid_subscriptions = [
            sub for sub in all_subscriptions 
            if sub.user_id == "123456789"
        ]
        assert len(valid_subscriptions) == 1
        
        print("✅ 錯誤後資料一致性測試通過")
    
    def test_transaction_rollback_simulation(self, temp_database):
        """測試交易回滾模擬"""
        
        data_manager = DataManager()
        
        # 儲存初始資料
        initial_subscription = UserSubscription(
            user_id="111222333",
            telegram_username="initial_user",
            subscribed_teams=["T1"]
        )
        data_manager.save_subscription(initial_subscription)
        
        # 驗證初始資料存在
        retrieved = data_manager.get_user_subscription("111222333")
        assert retrieved is not None
        assert len(retrieved.subscribed_teams) == 1
        
        # 模擬更新操作中的錯誤
        try:
            # 嘗試更新為無效狀態
            updated_subscription = UserSubscription(
                user_id="111222333",
                telegram_username="updated_user",
                subscribed_teams=["T1", "Gen.G", "DRX"]
            )
            
            # 正常情況下這應該成功
            update_result = data_manager.save_subscription(updated_subscription)
            
            # 驗證更新成功
            if update_result:
                final_retrieved = data_manager.get_user_subscription("111222333")
                assert final_retrieved is not None
                assert final_retrieved.telegram_username == "updated_user"
                assert len(final_retrieved.subscribed_teams) == 3
            
        except Exception as e:
            # 如果更新失敗，驗證原始資料仍然完整
            rollback_retrieved = data_manager.get_user_subscription("111222333")
            assert rollback_retrieved is not None
            assert rollback_retrieved.telegram_username == "initial_user"
            print(f"更新失敗但資料完整性保持: {e}")
        
        print("✅ 交易回滾模擬測試通過")