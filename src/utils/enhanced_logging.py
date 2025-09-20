"""
增強的日誌系統
提供多層級日誌記錄和監控功能
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import json
from pathlib import Path

class JSONFormatter(logging.Formatter):
    """JSON 格式的日誌格式化器"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加異常資訊
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加額外的上下文資訊
        if hasattr(record, 'context'):
            log_entry['context'] = record.context
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        
        return json.dumps(log_entry, ensure_ascii=False)

class ContextFilter(logging.Filter):
    """添加上下文資訊的過濾器"""
    
    def __init__(self):
        super().__init__()
        self.context = {}
    
    def filter(self, record):
        # 添加全域上下文資訊
        for key, value in self.context.items():
            setattr(record, key, value)
        return True
    
    def set_context(self, **kwargs):
        """設定上下文資訊"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """清除上下文資訊"""
        self.context.clear()

class EnhancedLogger:
    """增強的日誌記錄器"""
    
    def __init__(self, name: str = "lol_notification_system"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.context_filter = ContextFilter()
        self._setup_logging()
    
    def _setup_logging(self):
        """設定日誌系統"""
        # 清除現有的處理器
        self.logger.handlers.clear()
        
        # 設定日誌級別
        self.logger.setLevel(logging.DEBUG)
        
        # 確保日誌目錄存在
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 控制台處理器（彩色輸出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # 檔案處理器（詳細日誌）
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 錯誤日誌處理器（只記錄錯誤）
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        
        # JSON 日誌處理器（結構化日誌）
        json_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.json.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(JSONFormatter())
        
        # 添加上下文過濾器
        for handler in [console_handler, file_handler, error_handler, json_handler]:
            handler.addFilter(self.context_filter)
            self.logger.addHandler(handler)
        
        # 防止日誌重複
        self.logger.propagate = False
    
    def set_context(self, **kwargs):
        """設定日誌上下文"""
        self.context_filter.set_context(**kwargs)
    
    def clear_context(self):
        """清除日誌上下文"""
        self.context_filter.clear_context()
    
    def log_operation(self, operation: str, details: Dict[str, Any] = None, level: str = "INFO"):
        """記錄操作日誌"""
        message = f"操作: {operation}"
        if details:
            message += f" - 詳情: {details}"
        
        # 創建臨時記錄並添加操作資訊
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            __file__,
            0,
            message,
            (),
            None
        )
        record.operation = operation
        if details:
            record.context = details
        
        self.logger.handle(record)
    
    def log_api_call(self, api_name: str, endpoint: str, params: Dict[str, Any] = None, 
                     response_time: float = None, status: str = "SUCCESS"):
        """記錄 API 調用"""
        details = {
            'api_name': api_name,
            'endpoint': endpoint,
            'status': status
        }
        
        if params:
            details['params'] = params
        
        if response_time:
            details['response_time_ms'] = round(response_time * 1000, 2)
        
        level = "INFO" if status == "SUCCESS" else "ERROR"
        self.log_operation(f"API調用: {api_name}", details, level)
    
    def log_user_action(self, user_id: str, action: str, details: Dict[str, Any] = None):
        """記錄使用者操作"""
        message = f"使用者操作: {action}"
        if details:
            message += f" - {details}"
        
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            __file__,
            0,
            message,
            (),
            None
        )
        record.user_id = user_id
        record.operation = action
        if details:
            record.context = details
        
        self.logger.handle(record)
    
    def log_notification(self, user_id: str, match_info: Dict[str, Any], status: str):
        """記錄通知發送"""
        details = {
            'match_id': match_info.get('match_id'),
            'teams': f"{match_info.get('team1')} vs {match_info.get('team2')}",
            'status': status
        }
        
        self.log_user_action(user_id, "通知發送", details)
    
    def log_performance(self, operation: str, duration: float, details: Dict[str, Any] = None):
        """記錄效能指標"""
        perf_details = {
            'duration_ms': round(duration * 1000, 2),
            'operation': operation
        }
        
        if details:
            perf_details.update(details)
        
        level = "WARNING" if duration > 5.0 else "INFO"  # 超過5秒警告
        self.log_operation(f"效能監控: {operation}", perf_details, level)
    
    def get_logger(self) -> logging.Logger:
        """取得底層的 logger 物件"""
        return self.logger

# 全域日誌記錄器實例
enhanced_logger = EnhancedLogger()

# 便利函數
def get_logger(name: str = None) -> logging.Logger:
    """取得日誌記錄器"""
    if name:
        return logging.getLogger(name)
    return enhanced_logger.get_logger()

def set_log_context(**kwargs):
    """設定全域日誌上下文"""
    enhanced_logger.set_context(**kwargs)

def clear_log_context():
    """清除全域日誌上下文"""
    enhanced_logger.clear_context()

def log_operation(operation: str, details: Dict[str, Any] = None, level: str = "INFO"):
    """記錄操作"""
    enhanced_logger.log_operation(operation, details, level)

def log_api_call(api_name: str, endpoint: str, params: Dict[str, Any] = None, 
                 response_time: float = None, status: str = "SUCCESS"):
    """記錄 API 調用"""
    enhanced_logger.log_api_call(api_name, endpoint, params, response_time, status)

def log_user_action(user_id: str, action: str, details: Dict[str, Any] = None):
    """記錄使用者操作"""
    enhanced_logger.log_user_action(user_id, action, details)

def log_notification(user_id: str, match_info: Dict[str, Any], status: str):
    """記錄通知"""
    enhanced_logger.log_notification(user_id, match_info, status)

def log_performance(operation: str, duration: float, details: Dict[str, Any] = None):
    """記錄效能"""
    enhanced_logger.log_performance(operation, duration, details)

# 效能監控裝飾器
def monitor_performance(operation_name: str = None):
    """效能監控裝飾器"""
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log_performance(op_name, duration, {"status": "success"})
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_performance(op_name, duration, {"status": "error", "error": str(e)})
                raise
        
        return wrapper
    return decorator