"""
通知管理服務
處理通知邏輯和訊息格式化
"""

import uuid
from typing import List
from datetime import datetime, timedelta
import logging

from ..models import Match, UserSubscription, NotificationRecord
from .data_manager import DataManager
from .telegram_api import TelegramAPI
from ..utils.error_handler import NotificationError, notification_error_handler, safe_execute
from ..utils.enhanced_logging import log_notification, log_operation, monitor_performance

logger = logging.getLogger(__name__)

class NotificationManager:
    """通知管理類別"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.telegram_api = TelegramAPI()
    
    def create_match_notification(self, match: Match) -> str:
        """建立比賽通知訊息"""
        time_str = match.scheduled_time.strftime("%Y年%m月%d日 %H:%M")
        
        message = f"🎮 <b>LOL比賽提醒</b>\n\n" \
                 f"⚔️ <b>{match.team1.name}</b> vs <b>{match.team2.name}</b>\n" \
                 f"🏆 {match.tournament}\n" \
                 f"⏰ {time_str}\n" \
                 f"📺 {match.match_format}\n\n"
        
        if match.stream_url:
            message += f"🔗 <a href='{match.stream_url}'>觀看直播</a>\n\n"
        
        message += "祝您觀賽愉快！ 🎉"
        
        return message
    
    @notification_error_handler
    @monitor_performance("send_notifications_for_match")
    def send_notifications_for_match(self, match: Match) -> None:
        """為特定比賽發送通知給相關訂閱者"""
        try:
            # 取得所有訂閱者
            subscriptions = self.data_manager.get_all_subscriptions()
            
            # 找出訂閱了參賽戰隊的使用者
            relevant_users = []
            for subscription in subscriptions:
                if (match.team1.name in subscription.subscribed_teams or 
                    match.team2.name in subscription.subscribed_teams):
                    relevant_users.append(subscription)
            
            if not relevant_users:
                logger.info(f"比賽 {match.match_id} 沒有相關訂閱者")
                return
            
            # 建立通知訊息
            message = self.create_match_notification(match)
            
            # 發送通知給每個相關使用者
            for user in relevant_users:
                self._send_notification_to_user(user, match, message)
            
            log_operation(
                "批次通知發送完成",
                {
                    "match_id": match.match_id,
                    "teams": f"{match.team1.name} vs {match.team2.name}",
                    "notification_count": len(relevant_users)
                }
            )
            
        except Exception as e:
            logger.error(f"發送比賽通知時發生錯誤: {e}")
    
    def _send_notification_to_user(self, user: UserSubscription, match: Match, message: str) -> None:
        """發送通知給特定使用者"""
        try:
            # 建立通知記錄
            notification_record = NotificationRecord(
                notification_id=str(uuid.uuid4()),
                user_id=user.user_id,
                match_id=match.match_id,
                message=message
            )
            
            # 嘗試發送通知
            success = self.telegram_api.send_notification(user.user_id, message)
            
            if success:
                notification_record.mark_as_sent()
                log_notification(
                    user.user_id,
                    {
                        "match_id": match.match_id,
                        "team1": match.team1.name,
                        "team2": match.team2.name
                    },
                    "SUCCESS"
                )
            else:
                notification_record.mark_as_failed("Telegram API發送失敗")
                log_notification(
                    user.user_id,
                    {
                        "match_id": match.match_id,
                        "team1": match.team1.name,
                        "team2": match.team2.name
                    },
                    "FAILED"
                )
                raise NotificationError(f"發送通知給使用者 {user.user_id} 失敗", "TELEGRAM_SEND_FAILED")
            
            # 儲存通知記錄
            self.data_manager.save_notification_record(notification_record)
            
        except Exception as e:
            logger.error(f"發送通知給使用者 {user.user_id} 時發生錯誤: {e}")
    
    def get_subscribers_for_team(self, team_name: str) -> List[UserSubscription]:
        """取得訂閱特定戰隊的使用者列表"""
        try:
            all_subscriptions = self.data_manager.get_all_subscriptions()
            subscribers = []
            
            for subscription in all_subscriptions:
                if team_name in subscription.subscribed_teams:
                    subscribers.append(subscription)
            
            return subscribers
            
        except Exception as e:
            logger.error(f"取得戰隊 {team_name} 訂閱者時發生錯誤: {e}")
            return []
    
    def retry_failed_notifications(self) -> None:
        """重試失敗的通知"""
        try:
            # 取得最近的通知記錄
            recent_records = self.data_manager.get_notification_history(limit=100)
            
            # 找出可以重試的失敗通知
            failed_records = [
                record for record in recent_records 
                if record.can_retry() and 
                record.sent_at > datetime.now() - timedelta(hours=24)
            ]
            
            if not failed_records:
                logger.info("沒有需要重試的失敗通知")
                return
            
            # 重試每個失敗的通知
            for record in failed_records:
                try:
                    success = self.telegram_api.send_notification(
                        record.user_id, 
                        record.message
                    )
                    
                    if success:
                        record.mark_as_sent()
                        logger.info(f"重試通知 {record.notification_id} 成功")
                    else:
                        record.mark_as_failed("重試後仍然失敗")
                        logger.error(f"重試通知 {record.notification_id} 失敗")
                    
                    # 更新記錄
                    self.data_manager.save_notification_record(record)
                    
                except Exception as e:
                    logger.error(f"重試通知 {record.notification_id} 時發生錯誤: {e}")
            
            logger.info(f"完成重試 {len(failed_records)} 個失敗通知")
            
        except Exception as e:
            logger.error(f"重試失敗通知時發生錯誤: {e}")
    
    def send_test_notification(self, user_id: str) -> bool:
        """發送測試通知"""
        try:
            return self.telegram_api.send_test_message(user_id)
        except Exception as e:
            logger.error(f"發送測試通知時發生錯誤: {e}")
            return False