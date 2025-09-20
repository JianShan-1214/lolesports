"""
效能測試和優化
測試系統效能瓶頸並進行優化
"""

import pytest
import time
import threading
import psutil
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.services.data_manager import DataManager
from src.services.leaguepedia_api import LeaguepediaAPI
from src.services.telegram_api import TelegramAPI
from src.services.notification_manager import NotificationManager
from src.models.user import UserSubscription
from src.models.team import Team
from src.models.match import Match
from src.models.notification import NotificationRecord

from tests.fixtures.test_data import IntegrationTestHelper


class TestPerformance:
    """效能測試類別"""
    
    def setup_method(self):
        """設定測試環境"""
        IntegrationTestHelper.setup_test_environment()
        
        # 建立服務實例
        self.data_manager = DataManager()
        self.leaguepedia_api = LeaguepediaAPI()
        self.telegram_api = TelegramAPI()
        self.notification_manager = NotificationManager()
        
        # 記錄初始記憶體使用量
        self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    def teardown_method(self):
        """清理測試環境"""
        IntegrationTestHelper.cleanup_test_environment()
        
        # 記錄最終記憶體使用量
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - self.initial_memory
        print(f"記憶體使用變化: {memory_increase:.2f} MB")
    
    def test_data_cache_performance(self, temp_database, test_teams):
        """測試資料快取效能"""
        
        print("🔧 測試資料快取效能...")
        
        # 建立大量測試比賽資料
        large_match_dataset = []
        for i in range(1000):  # 1000場比賽
            match = Match(
                match_id=f"perf_match_{i:04d}",
                team1=test_teams[i % len(test_teams)],
                team2=test_teams[(i + 1) % len(test_teams)],
                scheduled_time=datetime.now() + timedelta(hours=i),
                tournament=f"Performance Test Tournament {i // 100}",
                match_format="BO3",
                status="scheduled"
            )
            large_match_dataset.append(match)
        
        # 測試快取寫入效能
        start_time = time.time()
        cache_result = self.data_manager.cache_match_data(large_match_dataset)
        cache_write_time = time.time() - start_time
        
        assert cache_result is True
        print(f"快取寫入 1000 場比賽耗時: {cache_write_time:.3f} 秒")
        
        # 效能要求：寫入1000場比賽應該在5秒內完成
        assert cache_write_time < 5.0, f"快取寫入效能不佳: {cache_write_time:.3f} 秒"
        
        # 測試快取讀取效能
        start_time = time.time()
        cached_matches = self.data_manager.get_cached_matches()
        cache_read_time = time.time() - start_time
        
        print(f"讀取 {len(cached_matches)} 場比賽耗時: {cache_read_time:.3f} 秒")
        
        # 效能要求：讀取應該在1秒內完成
        assert cache_read_time < 1.0, f"快取讀取效能不佳: {cache_read_time:.3f} 秒"
        
        # 驗證資料完整性
        assert len(cached_matches) >= 1000
        
        print("✅ 資料快取效能測試通過")
    
    @patch('src.services.telegram_api.TelegramAPI.send_notification')
    def test_notification_batch_performance(self, mock_send_notification, temp_database, test_teams):
        """測試通知發送效能和批次處理"""
        
        print("🔧 測試通知批次發送效能...")
        
        # 模擬成功的Telegram API回應
        mock_send_notification.return_value = True
        
        # 建立大量用戶訂閱
        large_subscription_dataset = []
        for i in range(500):  # 500個用戶
            subscription = UserSubscription(
                user_id=f"{1000000 + i:09d}",
                telegram_username=f"perf_user_{i:04d}",
                subscribed_teams=["T1", "Gen.G"]  # 都訂閱相同戰隊以觸發通知
            )
            large_subscription_dataset.append(subscription)
            self.data_manager.save_subscription(subscription)
        
        # 建立測試比賽
        test_match = Match(
            match_id="perf_batch_match",
            team1=test_teams[0],  # T1
            team2=test_teams[1],  # Gen.G
            scheduled_time=datetime.now() + timedelta(hours=1),
            tournament="Performance Test Tournament",
            match_format="BO3",
            status="scheduled"
        )
        
        # 測試批次通知發送效能
        start_time = time.time()
        self.notification_manager.send_notifications_for_match(test_match)
        batch_send_time = time.time() - start_time
        
        print(f"批次發送 500 個通知耗時: {batch_send_time:.3f} 秒")
        
        # 效能要求：批次發送500個通知應該在10秒內完成
        assert batch_send_time < 10.0, f"批次通知效能不佳: {batch_send_time:.3f} 秒"
        
        # 驗證所有通知都被發送
        assert mock_send_notification.call_count == 500
        
        # 檢查通知記錄
        notification_history = self.data_manager.get_notification_history(limit=500)
        assert len(notification_history) == 500
        
        print("✅ 通知批次發送效能測試通過")
    
    def test_memory_usage_under_load(self, temp_database, test_teams):
        """測試記憶體使用和資源管理"""
        
        print("🔧 測試記憶體使用情況...")
        
        # 記錄開始時的記憶體使用
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        print(f"測試開始記憶體使用: {start_memory:.2f} MB")
        
        # 建立大量資料並進行操作
        for batch in range(10):  # 10個批次
            # 每批次建立100個訂閱
            subscriptions = []
            for i in range(100):
                subscription = UserSubscription(
                    user_id=f"{batch * 100 + i + 2000000:09d}",
                    telegram_username=f"memory_test_user_{batch}_{i:03d}",
                    subscribed_teams=[test_teams[i % len(test_teams)].name]
                )
                subscriptions.append(subscription)
                self.data_manager.save_subscription(subscription)
            
            # 每批次建立50場比賽
            matches = []
            for i in range(50):
                match = Match(
                    match_id=f"memory_test_match_{batch}_{i:03d}",
                    team1=test_teams[i % len(test_teams)],
                    team2=test_teams[(i + 1) % len(test_teams)],
                    scheduled_time=datetime.now() + timedelta(hours=batch * 10 + i),
                    tournament=f"Memory Test Tournament {batch}",
                    match_format="BO3",
                    status="scheduled"
                )
                matches.append(match)
            
            self.data_manager.cache_match_data(matches)
            
            # 檢查記憶體使用
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - start_memory
            
            print(f"批次 {batch + 1}/10 完成，記憶體使用: {current_memory:.2f} MB (+{memory_increase:.2f} MB)")
            
            # 記憶體使用不應該無限制增長
            # 允許合理的記憶體增長，但不應該超過200MB
            assert memory_increase < 200, f"記憶體使用過多: {memory_increase:.2f} MB"
        
        # 最終記憶體檢查
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - start_memory
        
        print(f"測試完成，總記憶體增長: {total_memory_increase:.2f} MB")
        
        # 總記憶體增長應該在合理範圍內
        assert total_memory_increase < 300, f"總記憶體使用過多: {total_memory_increase:.2f} MB"
        
        print("✅ 記憶體使用測試通過")
    
    def test_concurrent_operations_performance(self, temp_database, test_teams):
        """測試並發操作效能"""
        
        print("🔧 測試並發操作效能...")
        
        # 並發操作結果
        results = []
        errors = []
        operation_times = []
        
        def concurrent_database_operation(thread_id: int):
            """並發資料庫操作"""
            try:
                start_time = time.time()
                
                # 建立資料管理器實例
                dm = DataManager()
                
                # 執行多個操作
                for i in range(20):  # 每個執行緒執行20個操作
                    # 建立訂閱
                    subscription = UserSubscription(
                        user_id=f"{thread_id * 1000 + i + 3000000:09d}",
                        telegram_username=f"concurrent_user_{thread_id}_{i:03d}",
                        subscribed_teams=[test_teams[i % len(test_teams)].name]
                    )
                    
                    # 儲存訂閱
                    save_result = dm.save_subscription(subscription)
                    if save_result:
                        results.append(f"thread_{thread_id}_save_{i}")
                    
                    # 讀取訂閱
                    retrieved = dm.get_user_subscription(subscription.user_id)
                    if retrieved:
                        results.append(f"thread_{thread_id}_read_{i}")
                
                operation_time = time.time() - start_time
                operation_times.append(operation_time)
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # 啟動多個並發執行緒
        threads = []
        thread_count = 5
        
        start_time = time.time()
        
        for i in range(thread_count):
            thread = threading.Thread(target=concurrent_database_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有執行緒完成
        for thread in threads:
            thread.join(timeout=30)  # 30秒超時
        
        total_time = time.time() - start_time
        
        print(f"並發操作完成，總耗時: {total_time:.3f} 秒")
        print(f"成功操作: {len(results)}")
        print(f"錯誤數量: {len(errors)}")
        
        if operation_times:
            avg_time = sum(operation_times) / len(operation_times)
            print(f"平均執行緒操作時間: {avg_time:.3f} 秒")
        
        # 效能要求
        assert total_time < 15.0, f"並發操作總時間過長: {total_time:.3f} 秒"
        assert len(results) > 0, "沒有成功的並發操作"
        assert len(errors) < len(results) * 0.1, f"錯誤率過高: {len(errors)}/{len(results)}"
        
        print("✅ 並發操作效能測試通過")
    
    @patch('src.services.leaguepedia_api.LeaguepediaAPI._make_request_with_retry')
    def test_api_response_time_performance(self, mock_make_request):
        """測試API回應時間效能"""
        
        print("🔧 測試API回應時間效能...")
        
        # 模擬API回應
        mock_make_request.return_value = {
            "cargoquery": [
                {
                    "title": {
                        "Team1": "T1",
                        "Team2": "Gen.G",
                        "DateTime UTC": "2025-12-20 18:00:00",
                        "OverviewPage": "LCK Spring 2025",
                        "BestOf": "3",
                        "Stream": "https://twitch.tv/lck",
                        "Winner": ""
                    }
                }
            ]
        }
        
        # 測試多次API調用的效能
        api_call_times = []
        
        for i in range(10):  # 測試10次API調用
            start_time = time.time()
            matches = self.leaguepedia_api.get_upcoming_matches(days=2)
            api_call_time = time.time() - start_time
            api_call_times.append(api_call_time)
            
            assert len(matches) > 0, f"API調用 {i+1} 沒有返回資料"
        
        # 計算統計資料
        avg_time = sum(api_call_times) / len(api_call_times)
        max_time = max(api_call_times)
        min_time = min(api_call_times)
        
        print(f"API調用效能統計:")
        print(f"  平均時間: {avg_time:.3f} 秒")
        print(f"  最大時間: {max_time:.3f} 秒")
        print(f"  最小時間: {min_time:.3f} 秒")
        
        # 效能要求
        assert avg_time < 0.5, f"API平均回應時間過長: {avg_time:.3f} 秒"
        assert max_time < 1.0, f"API最大回應時間過長: {max_time:.3f} 秒"
        
        print("✅ API回應時間效能測試通過")
    
    def test_database_query_optimization(self, temp_database, test_teams):
        """測試資料庫查詢優化"""
        
        print("🔧 測試資料庫查詢優化...")
        
        # 建立大量測試資料
        print("建立測試資料...")
        
        # 建立1000個訂閱
        for i in range(1000):
            subscription = UserSubscription(
                user_id=f"{i + 4000000:09d}",
                telegram_username=f"query_test_user_{i:04d}",
                subscribed_teams=[test_teams[i % len(test_teams)].name]
            )
            self.data_manager.save_subscription(subscription)
        
        # 建立500場比賽
        matches = []
        for i in range(500):
            match = Match(
                match_id=f"query_test_match_{i:04d}",
                team1=test_teams[i % len(test_teams)],
                team2=test_teams[(i + 1) % len(test_teams)],
                scheduled_time=datetime.now() + timedelta(hours=i),
                tournament=f"Query Test Tournament {i // 50}",
                match_format="BO3",
                status="scheduled"
            )
            matches.append(match)
        
        self.data_manager.cache_match_data(matches)
        
        print("測試資料建立完成，開始查詢效能測試...")
        
        # 測試各種查詢的效能
        query_tests = [
            ("取得所有訂閱", lambda: self.data_manager.get_all_subscriptions()),
            ("取得所有比賽", lambda: self.data_manager.get_cached_matches()),
            ("取得通知歷史", lambda: self.data_manager.get_notification_history(limit=100)),
            ("查詢特定用戶", lambda: self.data_manager.get_user_subscription("4000500")),
        ]
        
        for query_name, query_func in query_tests:
            start_time = time.time()
            result = query_func()
            query_time = time.time() - start_time
            
            print(f"{query_name}: {query_time:.3f} 秒 (返回 {len(result) if hasattr(result, '__len__') else '1' if result else '0'} 筆資料)")
            
            # 查詢效能要求：每個查詢應該在2秒內完成
            assert query_time < 2.0, f"{query_name} 查詢時間過長: {query_time:.3f} 秒"
        
        print("✅ 資料庫查詢優化測試通過")
    
    def test_system_resource_monitoring(self, temp_database):
        """測試系統資源監控"""
        
        print("🔧 測試系統資源監控...")
        
        # 記錄系統資源使用情況
        def get_system_stats():
            process = psutil.Process()
            return {
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'open_files': len(process.open_files()),
                'threads': process.num_threads()
            }
        
        # 記錄初始狀態
        initial_stats = get_system_stats()
        print(f"初始系統狀態: {initial_stats}")
        
        # 執行一系列操作
        operations = [
            "建立資料管理器",
            "執行資料庫操作",
            "處理API請求",
            "發送通知"
        ]
        
        stats_history = [initial_stats]
        
        for i, operation in enumerate(operations):
            print(f"執行操作: {operation}")
            
            if operation == "建立資料管理器":
                dm = DataManager()
            elif operation == "執行資料庫操作":
                # 執行一些資料庫操作
                for j in range(50):
                    subscription = UserSubscription(
                        user_id=f"{j + 5000000:09d}",
                        telegram_username=f"monitor_user_{j:03d}",
                        subscribed_teams=["T1"]
                    )
                    dm.save_subscription(subscription)
            elif operation == "處理API請求":
                # 模擬API處理
                api = LeaguepediaAPI()
                # 這會使用模擬資料
                matches = api.get_upcoming_matches(days=1)
            elif operation == "發送通知":
                # 模擬通知處理
                nm = NotificationManager()
                # 這裡不實際發送，只是建立管理器
            
            # 等待一下讓系統穩定
            time.sleep(0.5)
            
            # 記錄當前狀態
            current_stats = get_system_stats()
            stats_history.append(current_stats)
            
            print(f"操作後狀態: {current_stats}")
        
        # 分析資源使用趨勢
        final_stats = stats_history[-1]
        
        memory_increase = final_stats['memory_mb'] - initial_stats['memory_mb']
        thread_increase = final_stats['threads'] - initial_stats['threads']
        
        print(f"資源使用變化:")
        print(f"  記憶體增長: {memory_increase:.2f} MB")
        print(f"  執行緒增長: {thread_increase}")
        print(f"  開啟檔案數: {final_stats['open_files']}")
        
        # 資源使用限制
        assert memory_increase < 100, f"記憶體增長過多: {memory_increase:.2f} MB"
        assert thread_increase < 10, f"執行緒增長過多: {thread_increase}"
        assert final_stats['open_files'] < 50, f"開啟檔案過多: {final_stats['open_files']}"
        
        print("✅ 系統資源監控測試通過")


class TestPerformanceOptimization:
    """效能優化測試類別"""
    
    def setup_method(self):
        """設定測試環境"""
        IntegrationTestHelper.setup_test_environment()
    
    def teardown_method(self):
        """清理測試環境"""
        IntegrationTestHelper.cleanup_test_environment()
    
    def test_identify_performance_bottlenecks(self, temp_database, test_teams):
        """識別效能瓶頸"""
        
        print("🔧 識別系統效能瓶頸...")
        
        # 測試各個組件的效能
        components = {
            'data_manager': DataManager(),
            'leaguepedia_api': LeaguepediaAPI(),
            'telegram_api': TelegramAPI(),
            'notification_manager': NotificationManager()
        }
        
        bottlenecks = []
        
        # 測試資料管理器效能
        print("測試資料管理器效能...")
        start_time = time.time()
        
        dm = components['data_manager']
        for i in range(100):
            subscription = UserSubscription(
                user_id=f"{i + 6000000:09d}",
                telegram_username=f"bottleneck_user_{i:03d}",
                subscribed_teams=["T1"]
            )
            dm.save_subscription(subscription)
        
        dm_time = time.time() - start_time
        print(f"資料管理器 100 次操作耗時: {dm_time:.3f} 秒")
        
        if dm_time > 2.0:
            bottlenecks.append(f"資料管理器效能瓶頸: {dm_time:.3f} 秒")
        
        # 測試API效能（使用模擬資料）
        print("測試API效能...")
        start_time = time.time()
        
        api = components['leaguepedia_api']
        for i in range(10):
            matches = api.get_upcoming_matches(days=1)
        
        api_time = time.time() - start_time
        print(f"API 10 次調用耗時: {api_time:.3f} 秒")
        
        if api_time > 5.0:
            bottlenecks.append(f"API效能瓶頸: {api_time:.3f} 秒")
        
        # 報告瓶頸
        if bottlenecks:
            print("發現效能瓶頸:")
            for bottleneck in bottlenecks:
                print(f"  - {bottleneck}")
        else:
            print("未發現明顯的效能瓶頸")
        
        # 提供優化建議
        optimization_suggestions = []
        
        if dm_time > 1.0:
            optimization_suggestions.append("建議優化資料庫索引和查詢")
        
        if api_time > 3.0:
            optimization_suggestions.append("建議實作API回應快取")
        
        if optimization_suggestions:
            print("優化建議:")
            for suggestion in optimization_suggestions:
                print(f"  - {suggestion}")
        
        print("✅ 效能瓶頸識別完成")
    
    def test_caching_optimization(self, temp_database, test_teams):
        """測試快取優化"""
        
        print("🔧 測試快取優化策略...")
        
        dm = DataManager()
        
        # 測試無快取的效能
        print("測試無快取效能...")
        
        no_cache_times = []
        for i in range(5):
            start_time = time.time()
            
            # 模擬重複查詢
            all_subscriptions = dm.get_all_subscriptions()
            cached_matches = dm.get_cached_matches()
            
            query_time = time.time() - start_time
            no_cache_times.append(query_time)
        
        avg_no_cache_time = sum(no_cache_times) / len(no_cache_times)
        print(f"無快取平均查詢時間: {avg_no_cache_time:.3f} 秒")
        
        # 模擬實作快取後的效能改善
        # 這裡我們假設快取能帶來50%的效能提升
        simulated_cache_time = avg_no_cache_time * 0.5
        
        print(f"預期快取優化後時間: {simulated_cache_time:.3f} 秒")
        print(f"預期效能提升: {((avg_no_cache_time - simulated_cache_time) / avg_no_cache_time * 100):.1f}%")
        
        # 快取優化建議
        cache_recommendations = [
            "實作記憶體快取以減少資料庫查詢",
            "使用Redis或類似的快取系統",
            "實作查詢結果快取機制",
            "設定合適的快取過期時間"
        ]
        
        print("快取優化建議:")
        for recommendation in cache_recommendations:
            print(f"  - {recommendation}")
        
        print("✅ 快取優化測試完成")
    
    def test_database_optimization(self, temp_database):
        """測試資料庫優化"""
        
        print("🔧 測試資料庫優化策略...")
        
        import sqlite3
        
        # 檢查資料庫結構
        with sqlite3.connect(temp_database) as conn:
            cursor = conn.cursor()
            
            # 檢查索引
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = cursor.fetchall()
            
            print(f"現有索引: {[idx[0] for idx in indexes]}")
            
            # 分析查詢計劃
            cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM user_subscriptions WHERE user_id = ?", ("123456789",))
            query_plan = cursor.fetchall()
            
            print("查詢計劃分析:")
            for step in query_plan:
                print(f"  {step}")
        
        # 資料庫優化建議
        db_optimizations = [
            "在user_id欄位上建立索引以加速查詢",
            "在scheduled_time欄位上建立索引以優化時間範圍查詢",
            "考慮使用複合索引優化多欄位查詢",
            "定期執行VACUUM以優化資料庫檔案大小",
            "使用ANALYZE更新查詢優化器統計資料"
        ]
        
        print("資料庫優化建議:")
        for optimization in db_optimizations:
            print(f"  - {optimization}")
        
        print("✅ 資料庫優化測試完成")


def run_performance_tests():
    """執行效能測試的主函數"""
    
    print("🚀 開始執行效能測試套件...")
    
    # 設定pytest參數
    pytest_args = [
        'tests/integration/test_performance.py',
        '-v',
        '--tb=short',
        '--durations=0',  # 顯示所有測試的執行時間
        '--color=yes'
    ]
    
    # 執行測試
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n🎉 所有效能測試通過！")
    else:
        print(f"\n❌ 效能測試失敗，退出碼: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    """命令列執行入口"""
    import sys
    exit_code = run_performance_tests()
    sys.exit(exit_code)