#!/usr/bin/env python3
"""
測試增強的系統功能
包括錯誤處理、日誌系統和監控
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.enhanced_logging import enhanced_logger, log_operation, log_api_call, monitor_performance
from src.utils.error_handler import error_handler, handle_exceptions, APIError
from src.utils.system_monitor import system_monitor, start_monitoring, get_current_metrics, health_check
from src.services.leaguepedia_api import LeaguepediaAPI

def test_logging_system():
    """測試日誌系統"""
    print("=== 測試日誌系統 ===")
    
    logger = enhanced_logger.get_logger()
    
    # 測試基本日誌
    logger.info("這是一個測試資訊日誌")
    logger.warning("這是一個測試警告日誌")
    logger.error("這是一個測試錯誤日誌")
    
    # 測試操作日誌
    log_operation("測試操作", {"test_param": "test_value"})
    
    # 測試 API 調用日誌
    log_api_call("TestAPI", "/test/endpoint", {"param1": "value1"}, 0.5, "SUCCESS")
    
    print("✅ 日誌系統測試完成")

def test_error_handling():
    """測試錯誤處理系統"""
    print("\n=== 測試錯誤處理系統 ===")
    
    # 測試裝飾器錯誤處理
    @handle_exceptions(
        error_types=(ValueError, TypeError),
        context="test_function",
        user_message="測試函數發生錯誤",
        default_return="預設值"
    )
    def test_function_with_error():
        raise ValueError("這是一個測試錯誤")
    
    result = test_function_with_error()
    print(f"錯誤處理結果: {result}")
    
    # 測試自定義錯誤
    try:
        raise APIError("測試 API 錯誤", "TEST_ERROR", {"detail": "測試詳情"})
    except APIError as e:
        error_handler.handle_error(e, "test_api_error", "API 測試錯誤")
    
    # 取得錯誤摘要
    error_summary = error_handler.get_error_summary()
    print(f"錯誤摘要: {error_summary}")
    
    print("✅ 錯誤處理系統測試完成")

def test_monitoring_system():
    """測試監控系統"""
    print("\n=== 測試監控系統 ===")
    
    # 啟動監控（短時間測試）
    start_monitoring()
    
    # 等待收集一些指標
    print("收集系統指標中...")
    time.sleep(3)
    
    # 取得當前指標
    current_metrics = get_current_metrics()
    print(f"當前系統指標: {current_metrics}")
    
    # 健康檢查
    health_status = health_check()
    print(f"系統健康狀態: {health_status}")
    
    # 測試計數器
    system_monitor.increment_counter('api_calls_today', 5)
    system_monitor.set_counter('active_users', 10)
    
    print("✅ 監控系統測試完成")

@monitor_performance("test_api_performance")
def test_performance_monitoring():
    """測試效能監控"""
    print("\n=== 測試效能監控 ===")
    
    # 模擬一些工作
    time.sleep(1)
    
    # 測試 API 調用效能
    api = LeaguepediaAPI()
    start_time = time.time()
    
    try:
        matches = api.get_upcoming_matches(days=1)
        duration = time.time() - start_time
        
        log_api_call(
            "LeaguepediaAPI", 
            "get_upcoming_matches", 
            {"days": 1}, 
            duration, 
            "SUCCESS"
        )
        
        print(f"API 調用成功，耗時 {duration:.2f} 秒，取得 {len(matches)} 場比賽")
        
    except Exception as e:
        duration = time.time() - start_time
        log_api_call(
            "LeaguepediaAPI", 
            "get_upcoming_matches", 
            {"days": 1}, 
            duration, 
            "ERROR"
        )
        print(f"API 調用失敗: {e}")
    
    print("✅ 效能監控測試完成")

def test_integrated_system():
    """測試整合系統"""
    print("\n=== 測試整合系統 ===")
    
    # 設定日誌上下文
    enhanced_logger.set_context(
        test_session="integrated_test",
        user_id="test_user"
    )
    
    # 模擬一系列操作
    log_operation("開始整合測試")
    
    try:
        # 模擬 API 調用
        api = LeaguepediaAPI()
        teams = api.get_team_list()
        
        log_operation("取得戰隊列表", {"team_count": len(teams)})
        
        # 模擬一些錯誤
        try:
            raise ConnectionError("模擬網路連接錯誤")
        except ConnectionError as e:
            error_handler.handle_error(e, "network_test", "網路連接測試錯誤")
        
        # 更新監控計數器
        system_monitor.increment_counter('api_calls_today', 2)
        system_monitor.increment_counter('notifications_sent_today', 1)
        
        log_operation("整合測試完成", {"status": "success"})
        
    except Exception as e:
        error_handler.handle_error(e, "integrated_test", "整合測試發生錯誤")
    
    finally:
        # 清除日誌上下文
        enhanced_logger.clear_context()
    
    print("✅ 整合系統測試完成")

def main():
    """主測試函數"""
    print("開始測試增強的系統功能...\n")
    
    try:
        test_logging_system()
        test_error_handling()
        test_monitoring_system()
        test_performance_monitoring()
        test_integrated_system()
        
        print("\n🎉 所有測試完成！")
        
        # 顯示最終統計
        print("\n=== 最終統計 ===")
        error_summary = error_handler.get_error_summary()
        print(f"錯誤統計: {error_summary}")
        
        current_metrics = get_current_metrics()
        if current_metrics:
            print(f"系統指標: {current_metrics}")
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
    
    finally:
        # 停止監控
        system_monitor.stop_monitoring()

if __name__ == "__main__":
    main()