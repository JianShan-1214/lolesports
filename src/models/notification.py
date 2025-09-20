"""
通知記錄資料模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from ..utils.validators import validate_telegram_user_id, validate_match_id, validate_notification_message

@dataclass
class NotificationRecord:
    """通知記錄模型"""
    
    notification_id: str
    user_id: str
    match_id: str
    message: str
    sent_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # sent, failed, pending
    retry_count: int = 0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """初始化後處理"""
        if isinstance(self.sent_at, str):
            self.sent_at = datetime.fromisoformat(self.sent_at)
        
        # 驗證資料
        self.validate()
    
    def mark_as_sent(self) -> None:
        """標記為已發送"""
        self.status = "sent"
        self.sent_at = datetime.now()
    
    def mark_as_failed(self, error_message: str) -> None:
        """標記為發送失敗"""
        self.status = "failed"
        self.error_message = error_message
        self.retry_count += 1
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """檢查是否可以重試"""
        return self.status == "failed" and self.retry_count < max_retries
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'notification_id': self.notification_id,
            'user_id': self.user_id,
            'match_id': self.match_id,
            'message': self.message,
            'sent_at': self.sent_at.isoformat(),
            'status': self.status,
            'retry_count': self.retry_count,
            'error_message': self.error_message
        }
    
    def validate(self) -> None:
        """驗證資料完整性"""
        if not self.notification_id:
            raise ValueError("通知ID不能為空")
        
        is_valid, error_msg = validate_telegram_user_id(self.user_id)
        if not is_valid:
            raise ValueError(f"使用者ID驗證失敗: {error_msg}")
        
        is_valid, error_msg = validate_match_id(self.match_id)
        if not is_valid:
            raise ValueError(f"比賽ID驗證失敗: {error_msg}")
        
        is_valid, error_msg = validate_notification_message(self.message)
        if not is_valid:
            raise ValueError(f"通知訊息驗證失敗: {error_msg}")
        
        if self.status not in ['sent', 'failed', 'pending']:
            raise ValueError("通知狀態必須為 sent、failed 或 pending")
        
        if self.retry_count < 0:
            raise ValueError("重試次數不能為負數")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NotificationRecord':
        """從字典建立實例"""
        return cls(**data)