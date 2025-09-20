"""
測試資料和fixture管理
提供整合測試所需的測試資料
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
import tempfile
import os
from pathlib import Path

from src.models.user import UserSubscription
from src.models.team import Team
from src.models.match import Match
from src.models.notification import NotificationRecord


class TestDataFactory:
    """測試資料工廠類別"""
    
    @staticmethod
    def create_test_teams() -> List[Team]:
        """建立測試戰隊資料"""
        return [
            Team(
                team_id="t1",
                name="T1",
                region="KR",
                league="LCK",
                logo_url="https://example.com/t1_logo.png"
            ),
            Team(
                team_id="geng",
                name="Gen.G",
                region="KR",
                league="LCK",
                logo_url="https://example.com/geng_logo.png"
            ),
            Team(
                team_id="drx",
                name="DRX",
                region="KR",
                league="LCK",
                logo_url="https://example.com/drx_logo.png"
            ),
            Team(
                team_id="fnatic",
                name="Fnatic",
                region="EU",
                league="LEC",
                logo_url="https://example.com/fnatic_logo.png"
            ),
            Team(
                team_id="g2",
                name="G2 Esports",
                region="EU",
                league="LEC",
                logo_url="https://example.com/g2_logo.png"
            )
        ]
    
    @staticmethod
    def create_test_subscriptions() -> List[UserSubscription]:
        """建立測試訂閱資料"""
        return [
            UserSubscription(
                user_id="123456789",
                telegram_username="test_user_1",
                subscribed_teams=["T1", "Gen.G"]
            ),
            UserSubscription(
                user_id="987654321",
                telegram_username="test_user_2",
                subscribed_teams=["DRX", "Fnatic"]
            ),
            UserSubscription(
                user_id="555666777",
                telegram_username="test_user_3",
                subscribed_teams=["T1", "G2 Esports"]
            ),
            UserSubscription(
                user_id="111222333",
                telegram_username="test_user_4",
                subscribed_teams=["Gen.G", "DRX", "Fnatic"]
            )
        ]
    
    @staticmethod
    def create_test_matches(teams: List[Team]) -> List[Match]:
        """建立測試比賽資料"""
        now = datetime.now()
        
        return [
            # 即將開始的比賽（1小時後）
            Match(
                match_id="match_001",
                team1=teams[0],  # T1
                team2=teams[1],  # Gen.G
                scheduled_time=now + timedelta(hours=1),
                tournament="LCK Spring 2025",
                match_format="BO3",
                status="scheduled",
                stream_url="https://twitch.tv/lck"
            ),
            # 今天稍晚的比賽（6小時後）
            Match(
                match_id="match_002",
                team1=teams[2],  # DRX
                team2=teams[0],  # T1
                scheduled_time=now + timedelta(hours=6),
                tournament="LCK Spring 2025",
                match_format="BO3",
                status="scheduled",
                stream_url="https://twitch.tv/lck"
            ),
            # 明天的比賽
            Match(
                match_id="match_003",
                team1=teams[3],  # Fnatic
                team2=teams[4],  # G2 Esports
                scheduled_time=now + timedelta(days=1, hours=2),
                tournament="LEC Spring 2025",
                match_format="BO1",
                status="scheduled",
                stream_url="https://twitch.tv/lec"
            ),
            # 進行中的比賽
            Match(
                match_id="match_004",
                team1=teams[1],  # Gen.G
                team2=teams[2],  # DRX
                scheduled_time=now - timedelta(minutes=30),
                tournament="LCK Spring 2025",
                match_format="BO5",
                status="live",
                stream_url="https://twitch.tv/lck"
            ),
            # 已完成的比賽
            Match(
                match_id="match_005",
                team1=teams[0],  # T1
                team2=teams[3],  # Fnatic
                scheduled_time=now - timedelta(days=1),
                tournament="MSI 2024",
                match_format="BO1",
                status="completed"
            )
        ]
    
    @staticmethod
    def create_test_notifications(matches: List[Match], subscriptions: List[UserSubscription]) -> List[NotificationRecord]:
        """建立測試通知記錄"""
        notifications = []
        
        # 為第一個比賽建立通知記錄
        match = matches[0]  # T1 vs Gen.G
        message = f"🎮 LOL比賽提醒\n⚔️ {match.team1.name} vs {match.team2.name}\n🏆 {match.tournament}"
        
        # 找出訂閱了參賽戰隊的使用者
        for subscription in subscriptions:
            if (match.team1.name in subscription.subscribed_teams or 
                match.team2.name in subscription.subscribed_teams):
                
                notifications.append(NotificationRecord(
                    notification_id=f"notif_{match.match_id}_{subscription.user_id}",
                    user_id=subscription.user_id,
                    match_id=match.match_id,
                    message=message,
                    status="sent"
                ))
        
        return notifications
    
    @staticmethod
    def create_mock_api_responses() -> Dict[str, Any]:
        """建立模擬API回應資料"""
        return {
            "leaguepedia_matches": {
                "success": True,
                "data": [
                    {
                        "match_id": "lp_match_001",
                        "team1": "T1",
                        "team2": "Gen.G",
                        "scheduled_time": "2025-12-20T18:00:00Z",
                        "tournament": "LCK Spring 2025",
                        "match_format": "BO3",
                        "status": "scheduled",
                        "stream_url": "https://twitch.tv/lck"
                    },
                    {
                        "match_id": "lp_match_002",
                        "team1": "DRX",
                        "team2": "T1",
                        "scheduled_time": "2025-12-21T18:00:00Z",
                        "tournament": "LCK Spring 2025",
                        "match_format": "BO3",
                        "status": "scheduled",
                        "stream_url": "https://twitch.tv/lck"
                    }
                ]
            },
            "leaguepedia_teams": {
                "success": True,
                "data": [
                    {
                        "team_id": "t1",
                        "name": "T1",
                        "region": "KR",
                        "league": "LCK"
                    },
                    {
                        "team_id": "geng",
                        "name": "Gen.G",
                        "region": "KR",
                        "league": "LCK"
                    }
                ]
            },
            "telegram_success": {
                "ok": True,
                "result": {
                    "message_id": 123,
                    "date": 1640995200,
                    "chat": {
                        "id": 123456789,
                        "type": "private"
                    },
                    "text": "測試訊息"
                }
            },
            "telegram_bot_info": {
                "ok": True,
                "result": {
                    "id": 123456789,
                    "is_bot": True,
                    "first_name": "LOL通知Bot",
                    "username": "lol_notification_bot",
                    "can_join_groups": False,
                    "can_read_all_group_messages": False,
                    "supports_inline_queries": False
                }
            },
            "telegram_error": {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot was blocked by the user"
            }
        }


@pytest.fixture
def test_teams():
    """測試戰隊fixture"""
    return TestDataFactory.create_test_teams()


@pytest.fixture
def test_subscriptions():
    """測試訂閱fixture"""
    return TestDataFactory.create_test_subscriptions()


@pytest.fixture
def test_matches(test_teams):
    """測試比賽fixture"""
    return TestDataFactory.create_test_matches(test_teams)


@pytest.fixture
def test_notifications(test_matches, test_subscriptions):
    """測試通知記錄fixture"""
    return TestDataFactory.create_test_notifications(test_matches, test_subscriptions)


@pytest.fixture
def mock_api_responses():
    """模擬API回應fixture"""
    return TestDataFactory.create_mock_api_responses()


@pytest.fixture
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
def temp_config():
    """臨時配置fixture"""
    # 建立臨時配置檔案
    temp_config = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    
    test_config = {
        "telegram": {
            "bot_token": "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "api_url": "https://api.telegram.org/bot"
        },
        "leaguepedia": {
            "api_url": "https://lol.fandom.com/api.php",
            "user_agent": "LOL通知系統測試/1.0"
        },
        "database": {
            "path": "test_subscriptions.db"
        },
        "logging": {
            "level": "DEBUG",
            "file": "test_app.log"
        }
    }
    
    import json
    json.dump(test_config, temp_config)
    temp_config.close()
    
    yield temp_config.name
    
    # 清理
    try:
        os.unlink(temp_config.name)
    except:
        pass


class IntegrationTestHelper:
    """整合測試輔助工具類別"""
    
    @staticmethod
    def setup_test_environment():
        """設定測試環境"""
        # 確保測試目錄存在
        test_dirs = ['data', 'logs', 'logs/metrics']
        for dir_name in test_dirs:
            Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def cleanup_test_environment():
        """清理測試環境"""
        # 清理測試產生的檔案
        test_files = [
            'test_subscriptions.db',
            'test_app.log',
            'logs/test_app.log'
        ]
        
        for file_path in test_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass
    
    @staticmethod
    def verify_notification_sent(notification_record: NotificationRecord) -> bool:
        """驗證通知是否成功發送"""
        return (
            notification_record.status == "sent" and
            notification_record.sent_at is not None and
            notification_record.retry_count == 0
        )
    
    @staticmethod
    def verify_subscription_data(subscription: UserSubscription, expected_data: Dict[str, Any]) -> bool:
        """驗證訂閱資料是否正確"""
        return (
            subscription.user_id == expected_data.get('user_id') and
            subscription.telegram_username == expected_data.get('telegram_username') and
            subscription.subscribed_teams == expected_data.get('subscribed_teams') and
            subscription.is_active == expected_data.get('is_active', True)
        )
    
    @staticmethod
    def verify_match_data(match: Match, expected_data: Dict[str, Any]) -> bool:
        """驗證比賽資料是否正確"""
        return (
            match.match_id == expected_data.get('match_id') and
            match.team1.name == expected_data.get('team1') and
            match.team2.name == expected_data.get('team2') and
            match.tournament == expected_data.get('tournament') and
            match.status == expected_data.get('status')
        )