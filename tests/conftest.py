"""
pytest配置檔案
提供全域fixture和測試配置
"""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# 確保可以導入專案模組
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def test_session_setup():
    """測試會話級別的設定"""
    print("\n🚀 開始測試會話")
    
    # 建立測試目錄
    test_dirs = ['data', 'logs', 'logs/metrics']
    for dir_name in test_dirs:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    yield
    
    print("\n🧹 清理測試會話")


@pytest.fixture(scope="function")
def temp_test_dir():
    """臨時測試目錄fixture"""
    temp_dir = tempfile.mkdtemp(prefix="lol_test_")
    yield temp_dir
    
    # 清理臨時目錄
    try:
        shutil.rmtree(temp_dir)
    except:
        pass


@pytest.fixture(scope="function")
def temp_database():
    """臨時資料庫fixture"""
    # 建立臨時資料庫檔案
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    # 修改設定以使用臨時資料庫
    from config.settings import settings
    original_db_path = settings._config['database']['path']
    settings._config['database']['path'] = temp_db.name
    
    yield temp_db.name
    
    # 清理：恢復原始設定並刪除臨時檔案
    settings._config['database']['path'] = original_db_path
    try:
        os.unlink(temp_db.name)
    except:
        pass


@pytest.fixture
def test_teams():
    """測試戰隊fixture"""
    from tests.fixtures.test_data import TestDataFactory
    return TestDataFactory.create_test_teams()


@pytest.fixture
def test_subscriptions():
    """測試訂閱fixture"""
    from tests.fixtures.test_data import TestDataFactory
    return TestDataFactory.create_test_subscriptions()


@pytest.fixture
def test_matches(test_teams):
    """測試比賽fixture"""
    from tests.fixtures.test_data import TestDataFactory
    return TestDataFactory.create_test_matches(test_teams)


@pytest.fixture
def test_notifications(test_matches, test_subscriptions):
    """測試通知記錄fixture"""
    from tests.fixtures.test_data import TestDataFactory
    return TestDataFactory.create_test_notifications(test_matches, test_subscriptions)


@pytest.fixture
def mock_api_responses():
    """模擬API回應fixture"""
    from tests.fixtures.test_data import TestDataFactory
    return TestDataFactory.create_mock_api_responses()


@pytest.fixture(scope="function")
def mock_config():
    """模擬配置fixture"""
    return {
        "telegram": {
            "bot_token": "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_TEST_TOKEN",
            "api_url": "https://api.telegram.org/bot"
        },
        "leaguepedia": {
            "api_url": "https://lol.fandom.com/api.php",
            "user_agent": "LOL通知系統測試/1.0"
        },
        "database": {
            "path": ":memory:"  # 使用記憶體資料庫進行測試
        },
        "logging": {
            "level": "DEBUG",
            "file": "test_app.log"
        },
        "scheduler": {
            "match_check_interval": 300,  # 5分鐘
            "data_fetch_interval": 1800   # 30分鐘
        }
    }


@pytest.fixture(autouse=True)
def setup_test_logging():
    """自動設定測試日誌"""
    import logging
    
    # 設定測試專用的日誌配置
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 降低某些模組的日誌級別以減少噪音
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def pytest_configure(config):
    """pytest配置鉤子"""
    
    # 註冊自定義標記
    config.addinivalue_line(
        "markers", "integration: 標記為整合測試"
    )
    config.addinivalue_line(
        "markers", "unit: 標記為單元測試"
    )
    config.addinivalue_line(
        "markers", "slow: 標記為慢速測試"
    )
    config.addinivalue_line(
        "markers", "api: 標記為API測試"
    )
    config.addinivalue_line(
        "markers", "database: 標記為資料庫測試"
    )


def pytest_collection_modifyitems(config, items):
    """修改測試項目收集"""
    
    # 為整合測試添加標記
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # 為API相關測試添加標記
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.api)
        
        # 為資料庫相關測試添加標記
        if "database" in item.name.lower() or "data_manager" in item.name.lower():
            item.add_marker(pytest.mark.database)


def pytest_runtest_setup(item):
    """測試執行前的設定"""
    
    # 檢查是否需要跳過某些測試
    if item.get_closest_marker("slow") and not item.config.getoption("--runslow"):
        pytest.skip("需要 --runslow 選項來執行慢速測試")


def pytest_addoption(parser):
    """添加命令列選項"""
    
    parser.addoption(
        "--runslow", 
        action="store_true", 
        default=False, 
        help="執行標記為慢速的測試"
    )
    
    parser.addoption(
        "--integration-only",
        action="store_true",
        default=False,
        help="只執行整合測試"
    )
    
    parser.addoption(
        "--unit-only",
        action="store_true",
        default=False,
        help="只執行單元測試"
    )


def pytest_runtest_makereport(item, call):
    """測試報告生成鉤子"""
    
    if call.when == "call":
        # 在測試執行後記錄結果
        if call.excinfo is None:
            # 測試通過
            print(f"✅ {item.name}")
        else:
            # 測試失敗
            print(f"❌ {item.name}")


@pytest.fixture
def capture_logs():
    """捕獲日誌輸出的fixture"""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # 添加到根日誌記錄器
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    yield log_capture
    
    # 清理
    root_logger.removeHandler(handler)


@pytest.fixture
def mock_datetime():
    """模擬datetime的fixture"""
    from unittest.mock import Mock
    from datetime import datetime, timedelta
    
    # 建立固定的測試時間
    test_time = datetime(2025, 12, 20, 12, 0, 0)
    
    mock_dt = Mock()
    mock_dt.now.return_value = test_time
    mock_dt.utcnow.return_value = test_time
    
    # 提供一些常用的時間計算
    mock_dt.test_time = test_time
    mock_dt.one_hour_later = test_time + timedelta(hours=1)
    mock_dt.one_day_later = test_time + timedelta(days=1)
    mock_dt.one_hour_ago = test_time - timedelta(hours=1)
    
    return mock_dt


# 測試資料清理函數
def cleanup_test_files():
    """清理測試產生的檔案"""
    test_files = [
        'test_subscriptions.db',
        'test_app.log',
        'logs/test_app.log'
    ]
    
    for file_path in test_files:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"清理檔案 {file_path} 時發生錯誤: {e}")


# 在測試會話結束時清理
def pytest_sessionfinish(session, exitstatus):
    """測試會話結束時的清理"""
    cleanup_test_files()
    print(f"\n🏁 測試會話結束，退出狀態: {exitstatus}")