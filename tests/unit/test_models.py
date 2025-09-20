"""
資料模型單元測試
"""

import pytest
from datetime import datetime
from src.models.user import UserSubscription
from src.models.team import Team
from src.models.match import Match
from src.models.notification import NotificationRecord


class TestUserSubscription:
    """使用者訂閱模型測試"""
    
    def test_create_valid_subscription(self):
        """測試建立有效的訂閱"""
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1", "Gen.G"]
        )
        
        assert subscription.user_id == "123456789"
        assert subscription.telegram_username == "test_user"
        assert subscription.subscribed_teams == ["T1", "Gen.G"]
        assert subscription.is_active is True
        assert isinstance(subscription.created_at, datetime)
        assert isinstance(subscription.updated_at, datetime)
    
    def test_invalid_user_id(self):
        """測試無效的使用者ID"""
        with pytest.raises(ValueError, match="使用者ID錯誤"):
            UserSubscription(
                user_id="invalid",
                telegram_username="test_user",
                subscribed_teams=["T1"]
            )
    
    def test_invalid_username(self):
        """測試無效的使用者名稱"""
        with pytest.raises(ValueError, match="使用者名稱錯誤"):
            UserSubscription(
                user_id="123456789",
                telegram_username="123invalid",
                subscribed_teams=["T1"]
            )
    
    def test_empty_teams_list(self):
        """測試空的戰隊列表"""
        with pytest.raises(ValueError, match="至少需要訂閱一個戰隊"):
            UserSubscription(
                user_id="123456789",
                telegram_username="test_user",
                subscribed_teams=[]
            )
    
    def test_add_team(self):
        """測試新增戰隊"""
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1"]
        )
        
        original_updated_at = subscription.updated_at
        subscription.add_team("Gen.G")
        
        assert "Gen.G" in subscription.subscribed_teams
        assert subscription.updated_at > original_updated_at
    
    def test_add_duplicate_team(self):
        """測試新增重複戰隊"""
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1"]
        )
        
        subscription.add_team("T1")
        assert subscription.subscribed_teams.count("T1") == 1
    
    def test_remove_team(self):
        """測試移除戰隊"""
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1", "Gen.G"]
        )
        
        subscription.remove_team("T1")
        assert "T1" not in subscription.subscribed_teams
        assert "Gen.G" in subscription.subscribed_teams
    
    def test_is_subscribed_to_team(self):
        """測試檢查戰隊訂閱"""
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1", "Gen.G"]
        )
        
        assert subscription.is_subscribed_to_team("T1") is True
        assert subscription.is_subscribed_to_team("DRX") is False
    
    def test_to_dict(self):
        """測試轉換為字典"""
        subscription = UserSubscription(
            user_id="123456789",
            telegram_username="test_user",
            subscribed_teams=["T1"]
        )
        
        data = subscription.to_dict()
        
        assert data["user_id"] == "123456789"
        assert data["telegram_username"] == "test_user"
        assert data["subscribed_teams"] == ["T1"]
        assert data["is_active"] is True
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_from_dict(self):
        """測試從字典建立實例"""
        data = {
            "user_id": "123456789",
            "telegram_username": "test_user",
            "subscribed_teams": ["T1"],
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:00:00",
            "is_active": True
        }
        
        subscription = UserSubscription.from_dict(data)
        
        assert subscription.user_id == "123456789"
        assert subscription.telegram_username == "test_user"
        assert subscription.subscribed_teams == ["T1"]


class TestTeam:
    """戰隊模型測試"""
    
    def test_create_valid_team(self):
        """測試建立有效的戰隊"""
        team = Team(
            team_id="t1",
            name="T1",
            region="KR",
            league="LCK"
        )
        
        assert team.team_id == "t1"
        assert team.name == "T1"
        assert team.region == "KR"
        assert team.league == "LCK"
        assert team.logo_url is None
    
    def test_invalid_team_id(self):
        """測試無效的戰隊ID"""
        with pytest.raises(ValueError, match="戰隊ID不能為空"):
            Team(
                team_id="",
                name="T1",
                region="KR",
                league="LCK"
            )
    
    def test_invalid_team_name(self):
        """測試無效的戰隊名稱"""
        with pytest.raises(ValueError, match="戰隊名稱驗證失敗"):
            Team(
                team_id="t1",
                name="",
                region="KR",
                league="LCK"
            )
    
    def test_empty_region(self):
        """測試空的地區"""
        with pytest.raises(ValueError, match="地區不能為空"):
            Team(
                team_id="t1",
                name="T1",
                region="",
                league="LCK"
            )
    
    def test_empty_league(self):
        """測試空的聯賽"""
        with pytest.raises(ValueError, match="聯賽不能為空"):
            Team(
                team_id="t1",
                name="T1",
                region="KR",
                league=""
            )
    
    def test_str_representation(self):
        """測試字串表示"""
        team = Team(
            team_id="t1",
            name="T1",
            region="KR",
            league="LCK"
        )
        
        assert str(team) == "T1 (KR)"
    
    def test_get_display_name(self):
        """測試取得顯示名稱"""
        team = Team(
            team_id="t1",
            name="T1",
            region="KR",
            league="LCK"
        )
        
        assert team.get_display_name() == "T1 - LCK"
    
    def test_to_dict(self):
        """測試轉換為字典"""
        team = Team(
            team_id="t1",
            name="T1",
            region="KR",
            league="LCK",
            logo_url="https://example.com/logo.png"
        )
        
        data = team.to_dict()
        
        assert data["team_id"] == "t1"
        assert data["name"] == "T1"
        assert data["region"] == "KR"
        assert data["league"] == "LCK"
        assert data["logo_url"] == "https://example.com/logo.png"
    
    def test_from_dict(self):
        """測試從字典建立實例"""
        data = {
            "team_id": "t1",
            "name": "T1",
            "region": "KR",
            "league": "LCK",
            "logo_url": None
        }
        
        team = Team.from_dict(data)
        
        assert team.team_id == "t1"
        assert team.name == "T1"
        assert team.region == "KR"
        assert team.league == "LCK"


class TestMatch:
    """比賽模型測試"""
    
    def setup_method(self):
        """設定測試資料"""
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
    
    def test_create_valid_match(self):
        """測試建立有效的比賽"""
        match = Match(
            match_id="match_001",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 18, 0),
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        assert match.match_id == "match_001"
        assert match.team1 == self.team1
        assert match.team2 == self.team2
        assert match.tournament == "LCK Spring 2024"
        assert match.match_format == "BO3"
        assert match.status == "scheduled"
    
    def test_invalid_match_id(self):
        """測試無效的比賽ID"""
        with pytest.raises(ValueError, match="比賽ID驗證失敗"):
            Match(
                match_id="",
                team1=self.team1,
                team2=self.team2,
                scheduled_time=datetime(2024, 1, 15, 18, 0),
                tournament="LCK Spring 2024",
                match_format="BO3",
                status="scheduled"
            )
    
    def test_invalid_match_format(self):
        """測試無效的比賽格式"""
        with pytest.raises(ValueError, match="比賽格式必須為 BO1、BO3 或 BO5"):
            Match(
                match_id="match_001",
                team1=self.team1,
                team2=self.team2,
                scheduled_time=datetime(2024, 1, 15, 18, 0),
                tournament="LCK Spring 2024",
                match_format="BO7",
                status="scheduled"
            )
    
    def test_invalid_status(self):
        """測試無效的比賽狀態"""
        with pytest.raises(ValueError, match="比賽狀態必須為 scheduled、live 或 completed"):
            Match(
                match_id="match_001",
                team1=self.team1,
                team2=self.team2,
                scheduled_time=datetime(2024, 1, 15, 18, 0),
                tournament="LCK Spring 2024",
                match_format="BO3",
                status="invalid"
            )
    
    def test_same_teams(self):
        """測試相同戰隊的比賽"""
        with pytest.raises(ValueError, match="比賽的兩個戰隊不能相同"):
            Match(
                match_id="match_001",
                team1=self.team1,
                team2=self.team1,
                scheduled_time=datetime(2024, 1, 15, 18, 0),
                tournament="LCK Spring 2024",
                match_format="BO3",
                status="scheduled"
            )
    
    def test_get_teams(self):
        """測試取得參賽戰隊列表"""
        match = Match(
            match_id="match_001",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 18, 0),
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        teams = match.get_teams()
        assert len(teams) == 2
        assert self.team1 in teams
        assert self.team2 in teams
    
    def test_has_team(self):
        """測試檢查比賽是否包含特定戰隊"""
        match = Match(
            match_id="match_001",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 18, 0),
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        assert match.has_team("T1") is True
        assert match.has_team("Gen.G") is True
        assert match.has_team("DRX") is False
    
    def test_is_upcoming(self):
        """測試檢查比賽是否即將開始"""
        # 未來的比賽
        future_match = Match(
            match_id="match_001",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2025, 12, 15, 18, 0),
            tournament="LCK Spring 2025",
            match_format="BO3",
            status="scheduled"
        )
        
        assert future_match.is_upcoming() is True
        
        # 已完成的比賽
        completed_match = Match(
            match_id="match_002",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2023, 1, 15, 18, 0),
            tournament="LCK Spring 2023",
            match_format="BO3",
            status="completed"
        )
        
        assert completed_match.is_upcoming() is False
    
    def test_get_match_description(self):
        """測試取得比賽描述"""
        match = Match(
            match_id="match_001",
            team1=self.team1,
            team2=self.team2,
            scheduled_time=datetime(2024, 1, 15, 18, 0),
            tournament="LCK Spring 2024",
            match_format="BO3",
            status="scheduled"
        )
        
        description = match.get_match_description()
        
        assert "T1 vs Gen.G" in description
        assert "LCK Spring 2024" in description
        assert "2024-01-15 18:00" in description
        assert "BO3" in description


class TestNotificationRecord:
    """通知記錄模型測試"""
    
    def test_create_valid_notification(self):
        """測試建立有效的通知記錄"""
        notification = NotificationRecord(
            notification_id="notif_001",
            user_id="123456789",
            match_id="match_001",
            message="T1 vs Gen.G 比賽即將開始！"
        )
        
        assert notification.notification_id == "notif_001"
        assert notification.user_id == "123456789"
        assert notification.match_id == "match_001"
        assert notification.message == "T1 vs Gen.G 比賽即將開始！"
        assert notification.status == "pending"
        assert notification.retry_count == 0
        assert isinstance(notification.sent_at, datetime)
    
    def test_invalid_notification_id(self):
        """測試無效的通知ID"""
        with pytest.raises(ValueError, match="通知ID不能為空"):
            NotificationRecord(
                notification_id="",
                user_id="123456789",
                match_id="match_001",
                message="測試訊息"
            )
    
    def test_invalid_user_id(self):
        """測試無效的使用者ID"""
        with pytest.raises(ValueError, match="使用者ID驗證失敗"):
            NotificationRecord(
                notification_id="notif_001",
                user_id="invalid",
                match_id="match_001",
                message="測試訊息"
            )
    
    def test_invalid_message(self):
        """測試無效的訊息"""
        with pytest.raises(ValueError, match="通知訊息驗證失敗"):
            NotificationRecord(
                notification_id="notif_001",
                user_id="123456789",
                match_id="match_001",
                message=""
            )
    
    def test_invalid_status(self):
        """測試無效的狀態"""
        with pytest.raises(ValueError, match="通知狀態必須為 sent、failed 或 pending"):
            NotificationRecord(
                notification_id="notif_001",
                user_id="123456789",
                match_id="match_001",
                message="測試訊息",
                status="invalid"
            )
    
    def test_mark_as_sent(self):
        """測試標記為已發送"""
        notification = NotificationRecord(
            notification_id="notif_001",
            user_id="123456789",
            match_id="match_001",
            message="測試訊息"
        )
        
        original_sent_at = notification.sent_at
        notification.mark_as_sent()
        
        assert notification.status == "sent"
        assert notification.sent_at > original_sent_at
    
    def test_mark_as_failed(self):
        """測試標記為發送失敗"""
        notification = NotificationRecord(
            notification_id="notif_001",
            user_id="123456789",
            match_id="match_001",
            message="測試訊息"
        )
        
        notification.mark_as_failed("網路錯誤")
        
        assert notification.status == "failed"
        assert notification.error_message == "網路錯誤"
        assert notification.retry_count == 1
    
    def test_can_retry(self):
        """測試檢查是否可以重試"""
        notification = NotificationRecord(
            notification_id="notif_001",
            user_id="123456789",
            match_id="match_001",
            message="測試訊息",
            status="failed",
            retry_count=2
        )
        
        assert notification.can_retry() is True
        
        notification.retry_count = 3
        assert notification.can_retry() is False
        
        notification.status = "sent"
        assert notification.can_retry() is False