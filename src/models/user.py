"""
使用者訂閱資料模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from ..utils.validators import validate_subscription_data, validate_telegram_user_id, validate_telegram_username

@dataclass
class UserSubscription:
    """使用者訂閱模型"""
    
    user_id: str  # Telegram使用者ID
    telegram_username: str
    subscribed_teams: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def __post_init__(self):
        """初始化後處理"""
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        
        # 驗證資料
        self.validate()
    
    def add_team(self, team_name: str) -> None:
        """新增訂閱戰隊"""
        if team_name not in self.subscribed_teams:
            self.subscribed_teams.append(team_name)
            self.updated_at = datetime.now()
    
    def remove_team(self, team_name: str) -> None:
        """移除訂閱戰隊"""
        if team_name in self.subscribed_teams:
            self.subscribed_teams.remove(team_name)
            self.updated_at = datetime.now()
    
    def is_subscribed_to_team(self, team_name: str) -> bool:
        """檢查是否訂閱特定戰隊"""
        return team_name in self.subscribed_teams
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'user_id': self.user_id,
            'telegram_username': self.telegram_username,
            'subscribed_teams': self.subscribed_teams,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active
        }
    
    def validate(self) -> None:
        """驗證資料完整性"""
        is_valid, error_msg = validate_subscription_data(
            self.user_id, 
            self.telegram_username, 
            self.subscribed_teams
        )
        if not is_valid:
            raise ValueError(f"訂閱資料驗證失敗: {error_msg}")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserSubscription':
        """從字典建立實例"""
        return cls(**data)