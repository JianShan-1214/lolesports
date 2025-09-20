"""
資料管理服務
處理本地資料存儲和CRUD操作
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models import UserSubscription, Match, NotificationRecord
from config.settings import settings

class DataManager:
    """資料管理類別"""
    
    def __init__(self):
        self.db_path = settings.database_path
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化資料庫"""
        # 確保資料目錄存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 建立使用者訂閱表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    user_id TEXT PRIMARY KEY,
                    telegram_username TEXT NOT NULL,
                    subscribed_teams TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
            ''')
            
            # 建立比賽資料表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    match_id TEXT PRIMARY KEY,
                    match_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 建立通知記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_records (
                    notification_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    match_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT
                )
            ''')
            
            conn.commit()
    
    # 使用者訂閱相關方法
    def save_subscription(self, subscription: UserSubscription) -> bool:
        """儲存使用者訂閱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_subscriptions 
                    (user_id, telegram_username, subscribed_teams, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    subscription.user_id,
                    subscription.telegram_username,
                    json.dumps(subscription.subscribed_teams),
                    subscription.created_at.isoformat(),
                    subscription.updated_at.isoformat(),
                    int(subscription.is_active)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"儲存訂閱時發生錯誤: {e}")
            return False
    
    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """取得使用者訂閱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, telegram_username, subscribed_teams, 
                           created_at, updated_at, is_active
                    FROM user_subscriptions WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return UserSubscription(
                        user_id=row[0],
                        telegram_username=row[1],
                        subscribed_teams=json.loads(row[2]),
                        created_at=datetime.fromisoformat(row[3]),
                        updated_at=datetime.fromisoformat(row[4]),
                        is_active=bool(row[5])
                    )
                return None
        except Exception as e:
            print(f"取得訂閱時發生錯誤: {e}")
            return None
    
    def get_all_subscriptions(self) -> List[UserSubscription]:
        """取得所有使用者訂閱"""
        subscriptions = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, telegram_username, subscribed_teams,
                           created_at, updated_at, is_active
                    FROM user_subscriptions WHERE is_active = 1
                ''')
                
                for row in cursor.fetchall():
                    subscription = UserSubscription(
                        user_id=row[0],
                        telegram_username=row[1],
                        subscribed_teams=json.loads(row[2]),
                        created_at=datetime.fromisoformat(row[3]),
                        updated_at=datetime.fromisoformat(row[4]),
                        is_active=bool(row[5])
                    )
                    subscriptions.append(subscription)
        except Exception as e:
            print(f"取得所有訂閱時發生錯誤: {e}")
        
        return subscriptions
    
    def delete_subscription(self, user_id: str) -> bool:
        """刪除使用者訂閱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_subscriptions SET is_active = 0 
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"刪除訂閱時發生錯誤: {e}")
            return False
    
    # 比賽資料相關方法
    def cache_match_data(self, matches: List[Match]) -> bool:
        """快取比賽資料"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                for match in matches:
                    cursor.execute('''
                        INSERT OR REPLACE INTO matches 
                        (match_id, match_data, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        match.match_id,
                        json.dumps(match.to_dict()),
                        now,
                        now
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"快取比賽資料時發生錯誤: {e}")
            return False
    
    def get_cached_matches(self) -> List[Match]:
        """取得快取的比賽資料"""
        matches = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT match_data FROM matches')
                
                for row in cursor.fetchall():
                    match_data = json.loads(row[0])
                    match = Match.from_dict(match_data)
                    matches.append(match)
        except Exception as e:
            print(f"取得快取比賽資料時發生錯誤: {e}")
        
        return matches
    
    # 通知記錄相關方法
    def save_notification_record(self, record: NotificationRecord) -> bool:
        """儲存通知記錄"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO notification_records
                    (notification_id, user_id, match_id, message, sent_at, 
                     status, retry_count, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.notification_id,
                    record.user_id,
                    record.match_id,
                    record.message,
                    record.sent_at.isoformat(),
                    record.status,
                    record.retry_count,
                    record.error_message
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"儲存通知記錄時發生錯誤: {e}")
            return False
    
    def get_notification_history(self, limit: int = 100) -> List[NotificationRecord]:
        """取得通知歷史記錄"""
        records = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT notification_id, user_id, match_id, message, 
                           sent_at, status, retry_count, error_message
                    FROM notification_records 
                    ORDER BY sent_at DESC LIMIT ?
                ''', (limit,))
                
                for row in cursor.fetchall():
                    record = NotificationRecord(
                        notification_id=row[0],
                        user_id=row[1],
                        match_id=row[2],
                        message=row[3],
                        sent_at=datetime.fromisoformat(row[4]),
                        status=row[5],
                        retry_count=row[6],
                        error_message=row[7]
                    )
                    records.append(record)
        except Exception as e:
            print(f"取得通知歷史時發生錯誤: {e}")
        
        return records