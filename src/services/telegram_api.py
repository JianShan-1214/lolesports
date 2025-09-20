"""
Telegram Bot API客戶端
處理訊息發送和Bot操作
"""

import requests
from typing import Optional, Dict, Any
import logging
import time
import re

from config.settings import settings

logger = logging.getLogger(__name__)

class TelegramAPI:
    """Telegram Bot API客戶端類別"""
    
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.api_url = settings.get('telegram.api_url', 'https://api.telegram.org/bot')
        self.session = requests.Session()
        self.max_retries = 3
        self.retry_delay = 1  # 秒
        self.timeout = 30
    
    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """執行API請求並包含重試機制"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Telegram API請求嘗試 {attempt + 1}/{self.max_retries}: {method} {url}")
                
                if method.upper() == 'GET':
                    response = self.session.get(url, timeout=self.timeout, **kwargs)
                elif method.upper() == 'POST':
                    response = self.session.post(url, timeout=self.timeout, **kwargs)
                else:
                    raise ValueError(f"不支援的HTTP方法: {method}")
                
                response.raise_for_status()
                result = response.json()
                
                # 檢查Telegram API回應
                if not result.get('ok', False):
                    error_code = result.get('error_code', 0)
                    error_description = result.get('description', '未知錯誤')
                    
                    # 某些錯誤不需要重試
                    if error_code in [400, 401, 403, 404]:  # 客戶端錯誤
                        logger.error(f"Telegram API客戶端錯誤 {error_code}: {error_description}")
                        return result
                    
                    # 其他錯誤可以重試
                    raise requests.RequestException(f"Telegram API錯誤 {error_code}: {error_description}")
                
                logger.debug("Telegram API請求成功")
                return result
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"請求超時 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"連接錯誤 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                if e.response.status_code == 429:  # 速率限制
                    retry_after = int(e.response.headers.get('Retry-After', self.retry_delay))
                    logger.warning(f"遇到速率限制，等待 {retry_after} 秒後重試 (嘗試 {attempt + 1}/{self.max_retries})")
                    time.sleep(retry_after)
                    continue
                else:
                    logger.error(f"HTTP錯誤 {e.response.status_code}: {e}")
                    break  # 對於非速率限制的HTTP錯誤，不重試
                    
            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"請求異常 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                
            except Exception as e:
                last_exception = e
                logger.error(f"未預期的錯誤 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                break  # 對於未預期的錯誤，不重試
            
            # 如果不是最後一次嘗試，等待後重試
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)  # 指數退避
                logger.debug(f"等待 {delay} 秒後重試")
                time.sleep(delay)
        
        # 所有重試都失敗
        logger.error(f"Telegram API請求失敗，已重試 {self.max_retries} 次")
        if last_exception:
            raise last_exception
        return None
    
    def validate_user_id(self, user_id: str) -> bool:
        """驗證Telegram用戶ID格式"""
        if not user_id:
            return False
        
        # Telegram用戶ID應該是數字字串或以@開頭的用戶名
        if user_id.startswith('@'):
            # 用戶名格式驗證：@username (5-31字符，包含@符號)
            # 用戶名必須以字母開頭，可包含字母、數字和底線，總長度5-31字符
            username_pattern = r'^@[a-zA-Z][a-zA-Z0-9_]{3,29}$'
            return bool(re.match(username_pattern, user_id))
        else:
            # 數字ID格式驗證
            try:
                user_id_int = int(user_id)
                # Telegram用戶ID通常是正整數
                return user_id_int > 0
            except ValueError:
                return False
    
    def validate_chat_access(self, user_id: str) -> bool:
        """驗證是否可以向指定用戶發送訊息"""
        if not self.validate_user_id(user_id):
            logger.error(f"無效的用戶ID格式: {user_id}")
            return False
        
        try:
            url = f"{self.api_url}{self.bot_token}/getChat"
            params = {'chat_id': user_id}
            
            result = self._make_request_with_retry('GET', url, params=params)
            
            if result and result.get('ok'):
                chat_info = result.get('result', {})
                logger.info(f"用戶 {user_id} 聊天驗證成功: {chat_info.get('type', 'unknown')}")
                return True
            else:
                error_description = result.get('description', '未知錯誤') if result else '請求失敗'
                logger.warning(f"無法存取用戶 {user_id} 的聊天: {error_description}")
                return False
                
        except Exception as e:
            logger.error(f"驗證聊天存取權限時發生錯誤: {e}")
            return False
    
    def send_notification(self, user_id: str, message: str) -> bool:
        """發送通知訊息給使用者"""
        if not self.bot_token:
            logger.error("Telegram Bot Token未設定")
            return False
        
        if not self.validate_user_id(user_id):
            logger.error(f"無效的用戶ID: {user_id}")
            return False
        
        if not message or not message.strip():
            logger.error("訊息內容不能為空")
            return False
        
        try:
            logger.info(f"準備發送訊息給用戶 {user_id}")
            
            url = f"{self.api_url}{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': user_id,
                'text': message.strip(),
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            result = self._make_request_with_retry('POST', url, json=payload)
            
            if result and result.get('ok'):
                message_id = result.get('result', {}).get('message_id')
                logger.info(f"成功發送訊息給使用者 {user_id} (訊息ID: {message_id})")
                return True
            else:
                error_description = result.get('description', '未知錯誤') if result else '請求失敗'
                error_code = result.get('error_code') if result else None
                
                # 記錄具體的錯誤類型
                if error_code == 403:
                    logger.error(f"用戶 {user_id} 已封鎖Bot或尚未開始對話")
                elif error_code == 400:
                    logger.error(f"無效的用戶ID或訊息格式: {user_id}")
                else:
                    logger.error(f"發送訊息失敗 (錯誤碼: {error_code}): {error_description}")
                
                return False
                
        except Exception as e:
            logger.error(f"發送Telegram訊息時發生錯誤: {e}")
            return False
    
    def validate_bot_token(self) -> bool:
        """驗證Bot Token是否有效"""
        if not self.bot_token:
            logger.error("Bot Token未設定")
            return False
        
        # 驗證Token格式：數字:字母數字字符串
        token_pattern = r'^\d+:[a-zA-Z0-9_-]{35,}$'
        if not re.match(token_pattern, self.bot_token):
            logger.error("Bot Token格式無效")
            return False
        
        try:
            logger.info("驗證Telegram Bot Token")
            
            url = f"{self.api_url}{self.bot_token}/getMe"
            
            result = self._make_request_with_retry('GET', url)
            
            if result and result.get('ok'):
                bot_info = result.get('result', {})
                bot_username = bot_info.get('username', 'Unknown')
                bot_name = bot_info.get('first_name', 'Unknown')
                logger.info(f"Bot驗證成功: @{bot_username} ({bot_name})")
                return True
            else:
                error_description = result.get('description', '未知錯誤') if result else '請求失敗'
                logger.error(f"Bot Token驗證失敗: {error_description}")
                return False
                
        except Exception as e:
            logger.error(f"驗證Bot Token時發生錯誤: {e}")
            return False
    
    def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """取得Bot資訊"""
        if not self.bot_token:
            logger.error("Bot Token未設定")
            return None
        
        try:
            logger.info("取得Telegram Bot資訊")
            
            url = f"{self.api_url}{self.bot_token}/getMe"
            
            result = self._make_request_with_retry('GET', url)
            
            if result and result.get('ok'):
                bot_info = result.get('result')
                logger.info(f"成功取得Bot資訊: @{bot_info.get('username', 'Unknown')}")
                return bot_info
            else:
                error_description = result.get('description', '未知錯誤') if result else '請求失敗'
                logger.error(f"取得Bot資訊失敗: {error_description}")
                return None
                
        except Exception as e:
            logger.error(f"取得Bot資訊時發生錯誤: {e}")
            return None
    
    def send_test_message(self, user_id: str) -> bool:
        """發送測試訊息"""
        test_message = (
            "🎮 <b>LOL比賽通知系統測試訊息</b>\n\n"
            "✅ 如果您收到這則訊息，表示通知功能正常運作！\n\n"
            "📱 您現在可以開始訂閱您喜愛的戰隊，"
            "我們會在他們有比賽時及時通知您。"
        )
        
        return self.send_notification(user_id, test_message)
    
    def send_match_notification(self, user_id: str, match_info: Dict[str, Any]) -> bool:
        """發送比賽通知訊息"""
        try:
            # 格式化比賽通知訊息
            team1 = match_info.get('team1', '未知戰隊')
            team2 = match_info.get('team2', '未知戰隊')
            tournament = match_info.get('tournament', '未知賽事')
            match_time = match_info.get('match_time', '未知時間')
            match_format = match_info.get('match_format', 'BO1')
            stream_url = match_info.get('stream_url')
            
            message = (
                f"🏆 <b>{tournament}</b>\n\n"
                f"⚔️ <b>{team1}</b> vs <b>{team2}</b>\n"
                f"🕐 {match_time}\n"
                f"📊 {match_format}\n"
            )
            
            if stream_url:
                message += f"\n📺 <a href='{stream_url}'>觀看直播</a>"
            
            message += "\n\n🎮 祝您觀賽愉快！"
            
            return self.send_notification(user_id, message)
            
        except Exception as e:
            logger.error(f"格式化比賽通知訊息時發生錯誤: {e}")
            return False
    
    def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """取得Webhook資訊"""
        if not self.bot_token:
            logger.error("Bot Token未設定")
            return None
        
        try:
            url = f"{self.api_url}{self.bot_token}/getWebhookInfo"
            
            result = self._make_request_with_retry('GET', url)
            
            if result and result.get('ok'):
                return result.get('result')
            else:
                error_description = result.get('description', '未知錯誤') if result else '請求失敗'
                logger.error(f"取得Webhook資訊失敗: {error_description}")
                return None
                
        except Exception as e:
            logger.error(f"取得Webhook資訊時發生錯誤: {e}")
            return None