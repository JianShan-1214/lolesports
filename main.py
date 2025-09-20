"""
LOL比賽通知系統主應用程式
Streamlit應用程式進入點
"""

import streamlit as st
import atexit
import logging
from typing import Optional

from src.ui.subscription_page import render_subscription_page
from src.ui.management_page import render_management_page
from src.ui.status_page import render_status_page
from src.ui.matches_page import render_matches_page
from src.utils.logging_config import setup_logging
from src.utils.enhanced_logging import enhanced_logger, set_log_context, log_operation
from src.utils.system_monitor import start_monitoring, stop_monitoring, set_counter
from src.utils.error_handler import error_handler
from src.services.scheduler_manager import SchedulerManager
from config.settings import settings

# 全域調度器實例
_scheduler_manager: Optional[SchedulerManager] = None

def initialize_application():
    """初始化應用程式"""
    global _scheduler_manager
    
    try:
        # 設定日誌系統
        setup_logging()
        
        # 設定日誌上下文
        set_log_context(
            application="lol_notification_system",
            version="1.0.0",
            environment="production"
        )
        
        logger = enhanced_logger.get_logger()
        log_operation("應用程式啟動", {"component": "main_app"})
        
        # 啟動系統監控
        start_monitoring()
        
        # 驗證配置
        if not _validate_configuration():
            st.error("❌ 配置驗證失敗，請檢查設定檔")
            st.stop()
        
        # 初始化背景任務調度器
        if _scheduler_manager is None:
            _scheduler_manager = SchedulerManager()
            
            # 註冊應用程式關閉時的清理函數
            atexit.register(cleanup_application)
            
            log_operation("應用程式初始化完成", {"scheduler_initialized": True})
        
        return _scheduler_manager
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"應用程式初始化失敗: {e}")
        st.error(f"❌ 應用程式初始化失敗: {e}")
        st.stop()

def _validate_configuration() -> bool:
    """驗證應用程式配置"""
    try:
        # 檢查必要的配置項目
        required_settings = [
            'telegram.bot_token',
            'leaguepedia.api_url'
        ]
        
        for setting_key in required_settings:
            if not settings.get(setting_key):
                st.warning(f"⚠️ 缺少必要配置: {setting_key}")
                return False
        
        return True
        
    except Exception as e:
        logging.getLogger(__name__).error(f"配置驗證時發生錯誤: {e}")
        return False

def setup_page_config():
    """設定 Streamlit 頁面配置"""
    st.set_page_config(
        page_title="LOL比賽通知系統",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': "LOL比賽通知系統 - 讓您不錯過任何精彩比賽！"
        }
    )

def render_sidebar_navigation() -> str:
    """渲染側邊欄導航並返回選擇的頁面"""
    st.sidebar.title("🎮 LOL比賽通知系統")
    st.sidebar.markdown("---")
    
    # 頁面選擇
    page = st.sidebar.selectbox(
        "📋 選擇功能頁面",
        ["比賽查看", "戰隊訂閱", "訂閱管理", "系統狀態"],
        help="選擇您要使用的功能"
    )
    
    # 顯示系統資訊
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ 系統資訊")
    
    # 背景任務狀態指示器
    if _scheduler_manager:
        job_status = _scheduler_manager.get_job_status()
        if job_status['is_running']:
            st.sidebar.success("🟢 背景任務運行中")
        else:
            st.sidebar.error("🔴 背景任務已停止")
    else:
        st.sidebar.warning("🟡 背景任務未初始化")
    
    # 快速操作按鈕
    st.sidebar.markdown("### ⚡ 快速操作")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🔄 重啟任務", help="重新啟動背景任務"):
            if _scheduler_manager:
                try:
                    _scheduler_manager.stop_all_tasks()
                    _scheduler_manager.start_background_tasks()
                    st.sidebar.success("✅ 任務已重啟")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"❌ 重啟失敗: {e}")
    
    with col2:
        if st.button("📊 系統狀態", help="跳轉到系統狀態頁面"):
            st.session_state.page_override = "系統狀態"
            st.rerun()
    
    return page

def start_background_tasks():
    """啟動背景任務"""
    if _scheduler_manager and 'scheduler_started' not in st.session_state:
        try:
            _scheduler_manager.start_background_tasks()
            st.session_state.scheduler_started = True
            
            logger = logging.getLogger(__name__)
            logger.info("背景任務已啟動")
            
            # 顯示啟動成功訊息
            st.sidebar.success("🚀 背景任務已啟動")
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"啟動背景任務失敗: {e}")
            st.sidebar.error(f"❌ 背景任務啟動失敗: {e}")

def cleanup_application():
    """清理應用程式資源"""
    global _scheduler_manager
    
    try:
        if _scheduler_manager:
            _scheduler_manager.stop_all_tasks()
        
        # 停止系統監控
        stop_monitoring()
        
        log_operation("應用程式正常關閉")
        
    except Exception as e:
        logger = enhanced_logger.get_logger()
        logger.error(f"應用程式關閉時發生錯誤: {e}")

def render_main_content(page: str):
    """根據選擇的頁面渲染主要內容"""
    try:
        # 檢查是否有頁面覆蓋
        if 'page_override' in st.session_state:
            page = st.session_state.page_override
            del st.session_state.page_override
        
        # 渲染對應頁面
        if page == "比賽查看":
            render_matches_page()
        elif page == "戰隊訂閱":
            render_subscription_page()
        elif page == "訂閱管理":
            render_management_page()
        elif page == "系統狀態":
            render_status_page()
        else:
            st.error(f"❌ 未知的頁面: {page}")
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"渲染頁面 '{page}' 時發生錯誤: {e}")
        
        st.error(f"❌ 載入頁面時發生錯誤: {e}")
        st.info("請嘗試重新整理頁面或聯繫系統管理員")

def main():
    """主應用程式函數"""
    try:
        # 設定頁面配置
        setup_page_config()
        
        # 初始化應用程式
        scheduler_manager = initialize_application()
        
        # 渲染側邊欄導航
        selected_page = render_sidebar_navigation()
        
        # 啟動背景任務
        start_background_tasks()
        
        # 渲染主要內容
        render_main_content(selected_page)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"主應用程式執行時發生嚴重錯誤: {e}")
        
        st.error("❌ 系統發生嚴重錯誤")
        st.error(f"錯誤詳情: {e}")
        st.info("請聯繫系統管理員或重新啟動應用程式")

if __name__ == "__main__":
    main()