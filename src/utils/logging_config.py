"""
日誌配置模組
設定應用程式的日誌系統
"""

import logging
import logging.handlers
from pathlib import Path
from config.settings import settings

def setup_logging():
    """設定應用程式日誌系統"""
    
    # 取得日誌配置
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    log_file_path = settings.log_file_path
    
    # 確保日誌目錄存在
    log_dir = Path(log_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 建立日誌格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 設定根日誌記錄器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除現有的處理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 建立檔案處理器（帶輪轉）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 建立控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 控制台只顯示警告以上等級
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 設定第三方函式庫的日誌等級
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.INFO)
    
    # 記錄日誌系統啟動
    logger = logging.getLogger(__name__)
    logger.info("日誌系統已初始化")
    logger.info(f"日誌等級: {settings.log_level}")
    logger.info(f"日誌檔案: {log_file_path}")

def get_logger(name: str) -> logging.Logger:
    """取得指定名稱的日誌記錄器"""
    return logging.getLogger(name)