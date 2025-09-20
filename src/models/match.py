"""
比賽資料模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .team import Team
from ..utils.validators import validate_match_id

@dataclass
class Match:
    """比賽模型"""
    
    match_id: str
    team1: Team
    team2: Team
    scheduled_time: datetime
    tournament: str
    match_format: str  # BO1, BO3, BO5
    status: str  # scheduled, live, completed
    stream_url: Optional[str] = None
    
    def __post_init__(self):
        """初始化後處理"""
        if isinstance(self.scheduled_time, str):
            self.scheduled_time = datetime.fromisoformat(self.scheduled_time)
        
        # 驗證資料
        self.validate()
    
    def __str__(self) -> str:
        """字串表示"""
        return f"{self.team1.name} vs {self.team2.name} - {self.tournament}"
    
    def get_teams(self) -> list[Team]:
        """取得參賽戰隊列表"""
        return [self.team1, self.team2]
    
    def has_team(self, team_name: str) -> bool:
        """檢查比賽是否包含特定戰隊"""
        return team_name in [self.team1.name, self.team2.name]
    
    def is_upcoming(self) -> bool:
        """檢查比賽是否即將開始"""
        return self.status == "scheduled" and self.scheduled_time > datetime.now()
    
    def get_match_description(self) -> str:
        """取得比賽描述"""
        time_str = self.scheduled_time.strftime("%Y-%m-%d %H:%M")
        return f"{self.team1.name} vs {self.team2.name}\n" \
               f"🏆 {self.tournament}\n" \
               f"⏰ {time_str}\n" \
               f"📺 {self.match_format}"
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'match_id': self.match_id,
            'team1': self.team1.to_dict(),
            'team2': self.team2.to_dict(),
            'scheduled_time': self.scheduled_time.isoformat(),
            'tournament': self.tournament,
            'match_format': self.match_format,
            'status': self.status,
            'stream_url': self.stream_url
        }
    
    def validate(self) -> None:
        """驗證資料完整性"""
        is_valid, error_msg = validate_match_id(self.match_id)
        if not is_valid:
            raise ValueError(f"比賽ID驗證失敗: {error_msg}")
        
        if not self.tournament:
            raise ValueError("賽事名稱不能為空")
        
        if self.match_format not in ['BO1', 'BO3', 'BO5']:
            raise ValueError("比賽格式必須為 BO1、BO3 或 BO5")
        
        if self.status not in ['scheduled', 'live', 'completed']:
            raise ValueError("比賽狀態必須為 scheduled、live 或 completed")
        
        if self.team1.team_id == self.team2.team_id:
            raise ValueError("比賽的兩個戰隊不能相同")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Match':
        """從字典建立實例"""
        team1 = Team.from_dict(data['team1'])
        team2 = Team.from_dict(data['team2'])
        
        return cls(
            match_id=data['match_id'],
            team1=team1,
            team2=team2,
            scheduled_time=data['scheduled_time'],
            tournament=data['tournament'],
            match_format=data['match_format'],
            status=data['status'],
            stream_url=data.get('stream_url')
        )