"""
戰隊資料模型
"""

from dataclasses import dataclass
from typing import Optional
from ..utils.validators import validate_team_name

@dataclass
class Team:
    """戰隊模型"""
    
    team_id: str
    name: str
    region: str
    league: str
    logo_url: Optional[str] = None
    
    def __post_init__(self):
        """初始化後處理"""
        self.validate()
    
    def __str__(self) -> str:
        """字串表示"""
        return f"{self.name} ({self.region})"
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'team_id': self.team_id,
            'name': self.name,
            'region': self.region,
            'league': self.league,
            'logo_url': self.logo_url
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Team':
        """從字典建立實例"""
        return cls(**data)
    
    def validate(self) -> None:
        """驗證資料完整性"""
        if not self.team_id:
            raise ValueError("戰隊ID不能為空")
        
        is_valid, error_msg = validate_team_name(self.name)
        if not is_valid:
            raise ValueError(f"戰隊名稱驗證失敗: {error_msg}")
        
        if not self.region:
            raise ValueError("地區不能為空")
        
        if not self.league:
            raise ValueError("聯賽不能為空")
    
    def get_display_name(self) -> str:
        """取得顯示名稱"""
        return f"{self.name} - {self.league}"