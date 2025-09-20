"""
全域錯誤處理機制
提供統一的異常處理和錯誤恢復功能
"""

import logging
import traceback
import functools
from typing import Any, Callable, Optional, Dict, Type
from datetime import datetime
import streamlit as st

logger = logging.getLogger(__name__)

class ApplicationError(Exception):
    """應用程式基礎異常類別"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now()

class APIError(ApplicationError):
    """API 相關錯誤"""
    pass

class DataError(ApplicationError):
    """資料相關錯誤"""
    pass

class ValidationError(ApplicationError):
    """驗證相關錯誤"""
    pass

class NotificationError(ApplicationError):
    """通知相關錯誤"""
    pass

class ConfigurationError(ApplicationError):
    """配置相關錯誤"""
    pass

class ErrorHandler:
    """全域錯誤處理器"""
    
    def __init__(self):
        self.error_counts = {}
        self.last_errors = {}
        self.max_retries = 3
        self.error_threshold = 10  # 每小時最大錯誤數
    
    def handle_error(self, error: Exception, context: str = "", user_message: str = None) -> bool:
        """
        處理錯誤並決定是否需要重試
        
        Args:
            error: 發生的異常
            context: 錯誤發生的上下文
            user_message: 顯示給使用者的訊息
            
        Returns:
            bool: 是否應該重試
        """
        error_key = f"{type(error).__name__}:{context}"
        current_time = datetime.now()
        
        # 記錄錯誤
        self._log_error(error, context)
        
        # 更新錯誤計數
        if error_key not in self.error_counts:
            self.error_counts[error_key] = []
        
        self.error_counts[error_key].append(current_time)
        self.last_errors[error_key] = error
        
        # 清理舊的錯誤記錄（超過1小時）
        self._cleanup_old_errors()
        
        # 顯示使用者友善的錯誤訊息
        if user_message:
            self._show_user_error(user_message, error)
        
        # 決定是否重試
        return self._should_retry(error_key)
    
    def _log_error(self, error: Exception, context: str):
        """記錄錯誤詳情"""
        error_info = {
            'error_type': type(error).__name__,
            'message': str(error),
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        }
        
        if isinstance(error, ApplicationError):
            error_info.update({
                'error_code': error.error_code,
                'details': error.details
            })
        
        logger.error(f"錯誤發生在 {context}: {error_info}")
    
    def _show_user_error(self, message: str, error: Exception):
        """顯示使用者友善的錯誤訊息"""
        try:
            if hasattr(st, 'error'):
                st.error(f"❌ {message}")
                
                # 在開發模式下顯示詳細錯誤
                if st.session_state.get('debug_mode', False):
                    with st.expander("錯誤詳情 (開發模式)"):
                        st.code(str(error))
                        st.code(traceback.format_exc())
        except Exception:
            # 如果 Streamlit 不可用，只記錄到日誌
            logger.warning(f"無法顯示使用者錯誤訊息: {message}")
    
    def _should_retry(self, error_key: str) -> bool:
        """判斷是否應該重試"""
        recent_errors = [
            err_time for err_time in self.error_counts.get(error_key, [])
            if (datetime.now() - err_time).total_seconds() < 3600  # 1小時內
        ]
        
        return len(recent_errors) < self.error_threshold
    
    def _cleanup_old_errors(self):
        """清理超過1小時的錯誤記錄"""
        current_time = datetime.now()
        
        for error_key in list(self.error_counts.keys()):
            self.error_counts[error_key] = [
                err_time for err_time in self.error_counts[error_key]
                if (current_time - err_time).total_seconds() < 3600
            ]
            
            if not self.error_counts[error_key]:
                del self.error_counts[error_key]
                if error_key in self.last_errors:
                    del self.last_errors[error_key]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """取得錯誤摘要統計"""
        summary = {
            'total_error_types': len(self.error_counts),
            'recent_errors': {},
            'last_hour_total': 0
        }
        
        current_time = datetime.now()
        
        for error_key, error_times in self.error_counts.items():
            recent_count = len([
                t for t in error_times 
                if (current_time - t).total_seconds() < 3600
            ])
            
            if recent_count > 0:
                summary['recent_errors'][error_key] = {
                    'count': recent_count,
                    'last_occurrence': max(error_times).isoformat(),
                    'last_error': str(self.last_errors.get(error_key, ''))
                }
                summary['last_hour_total'] += recent_count
        
        return summary

# 全域錯誤處理器實例
error_handler = ErrorHandler()

def handle_exceptions(
    error_types: tuple = (Exception,),
    context: str = "",
    user_message: str = None,
    default_return: Any = None,
    retry_count: int = 3
):
    """
    裝飾器：自動處理函數中的異常
    
    Args:
        error_types: 要捕獲的異常類型
        context: 錯誤上下文描述
        user_message: 顯示給使用者的訊息
        default_return: 發生錯誤時的預設返回值
        retry_count: 重試次數
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)
                    
                except error_types as e:
                    last_exception = e
                    func_context = context or f"{func.__module__}.{func.__name__}"
                    
                    should_retry = error_handler.handle_error(
                        e, 
                        func_context,
                        user_message if attempt == retry_count else None
                    )
                    
                    if attempt < retry_count and should_retry:
                        logger.info(f"重試 {func_context} (嘗試 {attempt + 2}/{retry_count + 1})")
                        continue
                    else:
                        logger.error(f"{func_context} 最終失敗，返回預設值")
                        return default_return
                        
            return default_return
            
        return wrapper
    return decorator

def safe_execute(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    error_types: tuple = (Exception,),
    context: str = "",
    user_message: str = None,
    default_return: Any = None
) -> Any:
    """
    安全執行函數，自動處理異常
    
    Args:
        func: 要執行的函數
        args: 函數參數
        kwargs: 函數關鍵字參數
        error_types: 要捕獲的異常類型
        context: 錯誤上下文
        user_message: 使用者錯誤訊息
        default_return: 預設返回值
        
    Returns:
        函數執行結果或預設值
    """
    kwargs = kwargs or {}
    
    try:
        return func(*args, **kwargs)
    except error_types as e:
        func_context = context or f"{func.__module__}.{func.__name__}"
        error_handler.handle_error(e, func_context, user_message)
        return default_return

def create_graceful_degradation(
    primary_func: Callable,
    fallback_func: Callable,
    context: str = "",
    user_message: str = None
) -> Callable:
    """
    創建優雅降級函數：主要函數失敗時自動使用備用函數
    
    Args:
        primary_func: 主要函數
        fallback_func: 備用函數
        context: 錯誤上下文
        user_message: 使用者訊息
        
    Returns:
        包裝後的函數
    """
    def wrapper(*args, **kwargs):
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            func_context = context or f"{primary_func.__module__}.{primary_func.__name__}"
            error_handler.handle_error(e, func_context, user_message)
            
            logger.info(f"主要函數失敗，使用備用函數: {func_context}")
            try:
                return fallback_func(*args, **kwargs)
            except Exception as fallback_error:
                error_handler.handle_error(
                    fallback_error, 
                    f"{func_context}_fallback",
                    "系統暫時無法提供服務，請稍後再試"
                )
                return None
    
    return wrapper

# 常用的錯誤處理裝飾器
api_error_handler = handle_exceptions(
    error_types=(APIError, ConnectionError, TimeoutError),
    user_message="API 服務暫時無法使用，請稍後再試"
)

data_error_handler = handle_exceptions(
    error_types=(DataError, ValueError, KeyError),
    user_message="資料處理發生錯誤，請檢查輸入資料"
)

notification_error_handler = handle_exceptions(
    error_types=(NotificationError,),
    user_message="通知發送失敗，請檢查設定"
)