"""
背景任務調度管理服務
處理定期任務和自動化操作
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging

from .data_manager import DataManager
from .leaguepedia_api import LeaguepediaAPI
from .notification_manager import NotificationManager
from config.settings import settings

logger = logging.getLogger(__name__)

class SchedulerManager:
    """背景任務調度管理類別"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.data_manager = DataManager()
        self.leaguepedia_api = LeaguepediaAPI()
        self.notification_manager = NotificationManager()
        self._is_running = False
    
    def start_background_tasks(self) -> None:
        """啟動所有背景任務"""
        if self._is_running:
            logger.info("背景任務已經在運行中")
            return
        
        try:
            # 排程比賽資料獲取任務
            self.schedule_match_data_fetch()
            
            # 排程通知檢查任務
            self.schedule_notification_check()
            
            # 排程失敗通知重試任務
            self.schedule_retry_failed_notifications()
            
            # 啟動調度器
            self.scheduler.start()
            self._is_running = True
            
            logger.info("背景任務調度器已啟動")
            
        except Exception as e:
            logger.error(f"啟動背景任務時發生錯誤: {e}")
    
    def schedule_match_data_fetch(self) -> None:
        """排程比賽資料獲取任務"""
        try:
            # 取得配置的間隔時間（分鐘）
            interval_minutes = settings.get('scheduler.match_data_fetch_interval', 30)
            
            # 新增定期任務
            self.scheduler.add_job(
                func=self._fetch_match_data_job,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='fetch_match_data',
                name='獲取比賽資料',
                replace_existing=True
            )
            
            logger.info(f"已排程比賽資料獲取任務，間隔 {interval_minutes} 分鐘")
            
        except Exception as e:
            logger.error(f"排程比賽資料獲取任務時發生錯誤: {e}")
    
    def schedule_notification_check(self) -> None:
        """排程通知檢查任務"""
        try:
            # 取得配置的間隔時間（分鐘）
            interval_minutes = settings.get('scheduler.notification_check_interval', 5)
            
            # 新增定期任務
            self.scheduler.add_job(
                func=self._check_upcoming_matches_job,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='check_notifications',
                name='檢查即將開始的比賽',
                replace_existing=True
            )
            
            logger.info(f"已排程通知檢查任務，間隔 {interval_minutes} 分鐘")
            
        except Exception as e:
            logger.error(f"排程通知檢查任務時發生錯誤: {e}")
    
    def schedule_retry_failed_notifications(self) -> None:
        """排程失敗通知重試任務"""
        try:
            # 每小時重試一次失敗的通知
            self.scheduler.add_job(
                func=self._retry_failed_notifications_job,
                trigger=IntervalTrigger(hours=1),
                id='retry_failed_notifications',
                name='重試失敗通知',
                replace_existing=True
            )
            
            logger.info("已排程失敗通知重試任務，間隔 1 小時")
            
        except Exception as e:
            logger.error(f"排程失敗通知重試任務時發生錯誤: {e}")
    
    def _fetch_match_data_job(self) -> None:
        """比賽資料獲取任務"""
        try:
            logger.info("開始執行比賽資料獲取任務")
            
            # 獲取未來2天的比賽資料
            matches = self.leaguepedia_api.get_upcoming_matches(days=2)
            
            if matches:
                # 快取比賽資料
                success = self.data_manager.cache_match_data(matches)
                if success:
                    logger.info(f"成功快取 {len(matches)} 場比賽資料")
                else:
                    logger.error("快取比賽資料失敗")
            else:
                logger.info("沒有取得到比賽資料")
            
        except Exception as e:
            logger.error(f"執行比賽資料獲取任務時發生錯誤: {e}")
    
    def _check_upcoming_matches_job(self) -> None:
        """檢查即將開始的比賽任務"""
        try:
            logger.info("開始檢查即將開始的比賽")
            
            # 取得快取的比賽資料
            matches = self.data_manager.get_cached_matches()
            
            # 檢查即將在1小時內開始的比賽
            now = datetime.now()
            upcoming_matches = []
            
            for match in matches:
                time_diff = match.scheduled_time - now
                
                # 如果比賽在45-75分鐘內開始，發送通知
                if timedelta(minutes=45) <= time_diff <= timedelta(minutes=75):
                    upcoming_matches.append(match)
            
            # 為即將開始的比賽發送通知
            for match in upcoming_matches:
                self.notification_manager.send_notifications_for_match(match)
            
            if upcoming_matches:
                logger.info(f"為 {len(upcoming_matches)} 場即將開始的比賽發送了通知")
            
        except Exception as e:
            logger.error(f"檢查即將開始的比賽時發生錯誤: {e}")
    
    def _retry_failed_notifications_job(self) -> None:
        """重試失敗通知任務"""
        try:
            logger.info("開始重試失敗的通知")
            self.notification_manager.retry_failed_notifications()
            
        except Exception as e:
            logger.error(f"重試失敗通知時發生錯誤: {e}")
    
    def stop_all_tasks(self) -> None:
        """停止所有背景任務"""
        try:
            if self._is_running:
                self.scheduler.shutdown()
                self._is_running = False
                logger.info("背景任務調度器已停止")
            else:
                logger.info("背景任務調度器未在運行")
                
        except Exception as e:
            logger.error(f"停止背景任務時發生錯誤: {e}")
    
    def get_job_status(self) -> dict:
        """取得任務狀態"""
        try:
            jobs = self.scheduler.get_jobs()
            job_status = {}
            
            for job in jobs:
                job_status[job.id] = {
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
            
            return {
                'is_running': self._is_running,
                'jobs': job_status
            }
            
        except Exception as e:
            logger.error(f"取得任務狀態時發生錯誤: {e}")
            return {'is_running': False, 'jobs': {}}