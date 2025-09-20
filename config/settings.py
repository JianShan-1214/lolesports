"""
配置管理模組
處理應用程式配置和環境變數
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ConfigValidationError(Exception):
    """配置驗證錯誤"""
    message: str
    key: str
    
    def __str__(self):
        return f"配置驗證錯誤 [{self.key}]: {self.message}"

class Settings:
    """應用程式配置管理類別"""
    
    def __init__(self, config_file_path: Optional[str] = None):
        self.config_file = Path(config_file_path or "config/config.json")
        self.env_file = Path(".env")
        self.logger = logging.getLogger(__name__)
        self._config = self._load_config()
        self._load_env_file()
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置檔案"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.logger.info(f"成功載入配置檔案: {self.config_file}")
                    return config
            else:
                self.logger.warning(f"配置檔案不存在，使用預設配置: {self.config_file}")
                default_config = self._get_default_config()
                self._save_config_to_file(default_config)
                return default_config
                
        except json.JSONDecodeError as e:
            self.logger.error(f"配置檔案JSON格式錯誤: {e}")
            raise ConfigValidationError(f"JSON格式錯誤: {e}", str(self.config_file))
        except Exception as e:
            self.logger.error(f"載入配置檔案時發生錯誤: {e}")
            return self._get_default_config()
    
    def _load_env_file(self) -> None:
        """載入 .env 檔案"""
        if self.env_file.exists():
            try:
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                
                self.logger.info(f"成功載入環境變數檔案: {self.env_file}")
            except Exception as e:
                self.logger.warning(f"載入環境變數檔案時發生錯誤: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """取得預設配置"""
        return {
            "telegram": {
                "bot_token": "",
                "api_url": "https://api.telegram.org/bot",
                "timeout": 30,
                "retry_attempts": 3
            },
            "leaguepedia": {
                "api_url": "https://lol.fandom.com/api.php",
                "user_agent": "LOL-Match-Notification-System/1.0",
                "timeout": 30,
                "retry_attempts": 3,
                "rate_limit_delay": 1.0
            },
            "database": {
                "path": "data/subscriptions.db",
                "backup_enabled": True,
                "backup_interval_hours": 24
            },
            "scheduler": {
                "match_data_fetch_interval": 30,  # 分鐘
                "notification_check_interval": 5,  # 分鐘
                "timezone": "Asia/Taipei"
            },
            "logging": {
                "level": "INFO",
                "file_path": "logs/app.log",
                "max_file_size_mb": 10,
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "notification": {
                "advance_notice_minutes": 60,
                "max_retry_attempts": 3,
                "retry_delay_seconds": 300
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """取得配置值，支援環境變數覆蓋"""
        # 首先檢查環境變數
        env_key = key.upper().replace('.', '_')
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            # 嘗試轉換環境變數類型
            return self._convert_env_value(env_value)
        
        # 從配置檔案取得值
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """轉換環境變數值的類型"""
        # 布林值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 整數
        try:
            return int(value)
        except ValueError:
            pass
        
        # 浮點數
        try:
            return float(value)
        except ValueError:
            pass
        
        # 字串
        return value
    
    def set(self, key: str, value: Any) -> None:
        """設定配置值"""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self._save_config()
    
    def _save_config(self) -> None:
        """儲存配置到檔案"""
        self._save_config_to_file(self._config)
    
    def _save_config_to_file(self, config: Dict[str, Any]) -> None:
        """儲存配置到指定檔案"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置已儲存到: {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"儲存配置檔案時發生錯誤: {e}")
            raise ConfigValidationError(f"無法儲存配置檔案: {e}", str(self.config_file))
    
    def validate_configuration(self) -> List[str]:
        """驗證配置完整性，返回錯誤訊息列表"""
        errors = []
        
        # 驗證必要配置
        required_configs = [
            ('telegram.bot_token', '必須設定 Telegram Bot Token'),
            ('leaguepedia.api_url', '必須設定 Leaguepedia API URL'),
            ('database.path', '必須設定資料庫路徑'),
        ]
        
        for config_key, error_msg in required_configs:
            value = self.get(config_key)
            if not value:
                errors.append(f"{config_key}: {error_msg}")
        
        # 驗證數值範圍
        numeric_validations = [
            ('scheduler.match_data_fetch_interval', 1, 1440, '比賽資料獲取間隔必須在 1-1440 分鐘之間'),
            ('scheduler.notification_check_interval', 1, 60, '通知檢查間隔必須在 1-60 分鐘之間'),
            ('telegram.timeout', 1, 300, 'Telegram API 超時時間必須在 1-300 秒之間'),
            ('leaguepedia.timeout', 1, 300, 'Leaguepedia API 超時時間必須在 1-300 秒之間'),
        ]
        
        for config_key, min_val, max_val, error_msg in numeric_validations:
            value = self.get(config_key)
            if value is not None:
                try:
                    num_value = float(value)
                    if not (min_val <= num_value <= max_val):
                        errors.append(f"{config_key}: {error_msg}")
                except (ValueError, TypeError):
                    errors.append(f"{config_key}: 必須是數值")
        
        # 驗證路徑
        path_configs = [
            ('database.path', '資料庫路徑'),
            ('logging.file_path', '日誌檔案路徑'),
        ]
        
        for config_key, description in path_configs:
            path_value = self.get(config_key)
            if path_value:
                try:
                    path = Path(path_value)
                    # 確保父目錄存在
                    path.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"{config_key}: {description}無效 - {e}")
        
        return errors
    
    def create_env_template(self) -> None:
        """建立環境變數範本檔案"""
        env_template_path = Path(".env.template")
        
        template_content = """# LOL 比賽通知系統環境變數配置
# 複製此檔案為 .env 並填入實際值

# Telegram Bot 設定
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# 資料庫設定
DATABASE_PATH=data/subscriptions.db

# 日誌設定
LOGGING_LEVEL=INFO
LOGGING_FILE_PATH=logs/app.log

# 調度器設定
SCHEDULER_MATCH_DATA_FETCH_INTERVAL=30
SCHEDULER_NOTIFICATION_CHECK_INTERVAL=5

# API 設定
LEAGUEPEDIA_TIMEOUT=30
TELEGRAM_TIMEOUT=30
"""
        
        try:
            with open(env_template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            self.logger.info(f"環境變數範本已建立: {env_template_path}")
            
        except Exception as e:
            self.logger.error(f"建立環境變數範本時發生錯誤: {e}")
    
    def reload_config(self) -> None:
        """重新載入配置"""
        self._config = self._load_config()
        self._load_env_file()
        self.logger.info("配置已重新載入")
    
    # 便利屬性方法
    @property
    def telegram_bot_token(self) -> str:
        """取得Telegram Bot Token"""
        return self.get('telegram.bot_token', '')
    
    @property
    def telegram_api_url(self) -> str:
        """取得Telegram API URL"""
        return self.get('telegram.api_url', 'https://api.telegram.org/bot')
    
    @property
    def telegram_timeout(self) -> int:
        """取得Telegram API 超時時間"""
        return self.get('telegram.timeout', 30)
    
    @property
    def leaguepedia_api_url(self) -> str:
        """取得Leaguepedia API URL"""
        return self.get('leaguepedia.api_url', 'https://lol.fandom.com/api.php')
    
    @property
    def leaguepedia_user_agent(self) -> str:
        """取得Leaguepedia User Agent"""
        return self.get('leaguepedia.user_agent', 'LOL-Match-Notification-System/1.0')
    
    @property
    def database_path(self) -> str:
        """取得資料庫路徑"""
        return self.get('database.path', 'data/subscriptions.db')
    
    @property
    def log_level(self) -> str:
        """取得日誌等級"""
        return self.get('logging.level', 'INFO')
    
    @property
    def log_file_path(self) -> str:
        """取得日誌檔案路徑"""
        return self.get('logging.file_path', 'logs/app.log')
    
    @property
    def scheduler_timezone(self) -> str:
        """取得調度器時區"""
        return self.get('scheduler.timezone', 'Asia/Taipei')
    
    def get_all_config(self) -> Dict[str, Any]:
        """取得所有配置（隱藏敏感資訊）"""
        config_copy = self._config.copy()
        
        # 隱藏敏感資訊
        if 'telegram' in config_copy and 'bot_token' in config_copy['telegram']:
            token = config_copy['telegram']['bot_token']
            if token:
                config_copy['telegram']['bot_token'] = f"{token[:10]}...{token[-4:]}" if len(token) > 14 else "***"
        
        return config_copy

# 全域配置實例
settings = Settings()