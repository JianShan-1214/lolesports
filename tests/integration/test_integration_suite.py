"""
整合測試套件主檔案
統一管理和執行所有整合測試
"""

import pytest
import sys
import os
from pathlib import Path

# 確保可以導入專案模組
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures.test_data import IntegrationTestHelper


class TestIntegrationSuite:
    """整合測試套件管理類別"""
    
    @classmethod
    def setup_class(cls):
        """設定整個測試套件"""
        print("\n" + "="*60)
        print("🚀 開始執行LOL比賽通知系統整合測試套件")
        print("="*60)
        
        # 設定測試環境
        IntegrationTestHelper.setup_test_environment()
        
        # 檢查必要的依賴
        cls._check_dependencies()
        
        print("✅ 測試環境設定完成")
    
    @classmethod
    def teardown_class(cls):
        """清理整個測試套件"""
        print("\n" + "="*60)
        print("🧹 清理測試環境")
        print("="*60)
        
        # 清理測試環境
        IntegrationTestHelper.cleanup_test_environment()
        
        print("✅ 測試環境清理完成")
        print("🎉 整合測試套件執行完成")
        print("="*60)
    
    @classmethod
    def _check_dependencies(cls):
        """檢查測試依賴"""
        required_modules = [
            'src.models',
            'src.services',
            'src.utils',
            'config.settings'
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError as e:
                missing_modules.append(f"{module}: {e}")
        
        if missing_modules:
            print("❌ 缺少必要的模組:")
            for module in missing_modules:
                print(f"   - {module}")
            pytest.fail("缺少必要的依賴模組")
        else:
            print("✅ 所有必要模組都可用")
    
    def test_suite_configuration(self):
        """測試套件配置驗證"""
        
        # 驗證測試目錄結構
        test_dirs = [
            'tests/unit',
            'tests/integration',
            'tests/fixtures'
        ]
        
        for test_dir in test_dirs:
            assert Path(test_dir).exists(), f"測試目錄 {test_dir} 不存在"
        
        # 驗證測試檔案存在
        integration_test_files = [
            'tests/integration/test_end_to_end_flow.py',
            'tests/integration/test_api_integration.py',
            'tests/integration/test_error_scenarios.py'
        ]
        
        for test_file in integration_test_files:
            assert Path(test_file).exists(), f"測試檔案 {test_file} 不存在"
        
        print("✅ 測試套件配置驗證通過")
    
    def test_import_all_modules(self):
        """測試所有模組導入"""
        
        # 測試模型模組
        from src.models.user import UserSubscription
        from src.models.team import Team
        from src.models.match import Match
        from src.models.notification import NotificationRecord
        
        # 測試服務模組
        from src.services.data_manager import DataManager
        from src.services.leaguepedia_api import LeaguepediaAPI
        from src.services.telegram_api import TelegramAPI
        from src.services.notification_manager import NotificationManager
        from src.services.scheduler_manager import SchedulerManager
        
        # 測試工具模組
        from src.utils.enhanced_logging import log_operation
        from src.utils.error_handler import notification_error_handler
        from src.utils.system_monitor import SystemMonitor
        
        # 測試配置模組
        from config.settings import settings
        
        print("✅ 所有模組導入成功")
    
    def test_basic_functionality(self, temp_database):
        """測試基本功能可用性"""
        
        from src.services.data_manager import DataManager
        from src.models.user import UserSubscription
        
        # 測試資料管理器基本功能
        data_manager = DataManager()
        
        # 建立測試訂閱
        subscription = UserSubscription(
            user_id="999888777",
            telegram_username="suite_test_user",
            subscribed_teams=["T1"]
        )
        
        # 測試儲存
        save_result = data_manager.save_subscription(subscription)
        assert save_result is True
        
        # 測試讀取
        retrieved = data_manager.get_user_subscription("999888777")
        assert retrieved is not None
        assert retrieved.telegram_username == "suite_test_user"
        
        print("✅ 基本功能測試通過")


def run_integration_tests():
    """執行整合測試的主函數"""
    
    print("🔧 準備執行整合測試...")
    
    # 設定pytest參數
    pytest_args = [
        'tests/integration/',
        '-v',  # 詳細輸出
        '--tb=short',  # 簡短的錯誤追蹤
        '--durations=10',  # 顯示最慢的10個測試
        '--color=yes',  # 彩色輸出
        '-x',  # 遇到第一個失敗就停止
    ]
    
    # 如果有覆蓋率工具，加入覆蓋率參數
    try:
        import pytest_cov
        pytest_args.extend([
            '--cov=src',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov'
        ])
        print("✅ 啟用測試覆蓋率報告")
    except ImportError:
        print("⚠️  pytest-cov未安裝，跳過覆蓋率報告")
    
    # 執行測試
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n🎉 所有整合測試通過！")
    else:
        print(f"\n❌ 整合測試失敗，退出碼: {exit_code}")
    
    return exit_code


def run_specific_test_category(category: str):
    """執行特定類別的測試"""
    
    category_mapping = {
        'end_to_end': 'tests/integration/test_end_to_end_flow.py',
        'api': 'tests/integration/test_api_integration.py',
        'error': 'tests/integration/test_error_scenarios.py',
        'suite': 'tests/integration/test_integration_suite.py'
    }
    
    if category not in category_mapping:
        print(f"❌ 未知的測試類別: {category}")
        print(f"可用類別: {', '.join(category_mapping.keys())}")
        return 1
    
    test_file = category_mapping[category]
    
    print(f"🔧 執行 {category} 測試...")
    
    pytest_args = [
        test_file,
        '-v',
        '--tb=short',
        '--color=yes'
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print(f"\n✅ {category} 測試通過！")
    else:
        print(f"\n❌ {category} 測試失敗，退出碼: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    """命令列執行入口"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="LOL比賽通知系統整合測試套件")
    parser.add_argument(
        '--category', 
        choices=['end_to_end', 'api', 'error', 'suite', 'all'],
        default='all',
        help="要執行的測試類別"
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help="詳細輸出"
    )
    
    args = parser.parse_args()
    
    if args.category == 'all':
        exit_code = run_integration_tests()
    else:
        exit_code = run_specific_test_category(args.category)
    
    sys.exit(exit_code)