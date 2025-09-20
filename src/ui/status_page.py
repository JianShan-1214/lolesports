"""
系統狀態頁面
顯示系統運行狀態和日誌資訊
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import List

from ..services import DataManager, SchedulerManager, TelegramAPI, LeaguepediaAPI
from ..models import NotificationRecord
from ..utils.system_monitor import get_current_metrics, get_metrics_summary, health_check
from ..utils.error_handler import error_handler
from ..utils.enhanced_logging import enhanced_logger

def render_status_page():
    """渲染系統狀態頁面"""
    st.title("📊 系統狀態")
    st.markdown("監控系統運行狀態和通知歷史")
    
    # 初始化服務
    data_manager = DataManager()
    scheduler_manager = SchedulerManager()
    telegram_api = TelegramAPI()
    leaguepedia_api = LeaguepediaAPI()
    
    # 系統健康檢查
    _render_system_health(telegram_api, leaguepedia_api)
    
    # 系統監控指標
    _render_system_metrics()
    
    # 錯誤統計
    _render_error_statistics()
    
    # 背景任務狀態
    _render_scheduler_status(scheduler_manager)
    
    # 通知歷史
    _render_notification_history(data_manager)
    
    # 系統日誌
    _render_system_logs()

def _render_system_health(telegram_api: TelegramAPI, leaguepedia_api: LeaguepediaAPI):
    """渲染系統健康檢查"""
    
    st.subheader("🏥 系統健康檢查")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Telegram Bot 狀態**")
        
        if st.button("🔍 檢查 Telegram Bot"):
            with st.spinner("檢查中..."):
                is_valid = telegram_api.validate_bot_token()
                
                if is_valid:
                    bot_info = telegram_api.get_bot_info()
                    st.success("✅ Telegram Bot 連接正常")
                    if bot_info:
                        st.info(f"Bot 名稱: {bot_info.get('first_name', 'Unknown')}")
                        st.info(f"Bot 使用者名稱: @{bot_info.get('username', 'Unknown')}")
                else:
                    st.error("❌ Telegram Bot 連接失敗")
                    st.warning("請檢查Bot Token設定")
    
    with col2:
        st.write("**Leaguepedia API 狀態**")
        
        if st.button("🔍 檢查 Leaguepedia API"):
            with st.spinner("檢查中..."):
                try:
                    # 嘗試獲取少量資料來測試API
                    teams = leaguepedia_api.get_team_list()
                    
                    if teams:
                        st.success("✅ Leaguepedia API 連接正常")
                        st.info(f"成功取得 {len(teams)} 個戰隊資料")
                    else:
                        st.warning("⚠️ API 連接正常但沒有取得資料")
                        
                except Exception as e:
                    st.error("❌ Leaguepedia API 連接失敗")
                    st.error(f"錯誤: {str(e)}")

def _render_scheduler_status(scheduler_manager: SchedulerManager):
    """渲染背景任務狀態"""
    
    st.subheader("⏰ 背景任務狀態")
    
    try:
        job_status = scheduler_manager.get_job_status()
        
        # 顯示調度器狀態
        if job_status['is_running']:
            st.success("✅ 背景任務調度器正在運行")
        else:
            st.error("❌ 背景任務調度器未運行")
        
        # 顯示各個任務狀態
        if job_status['jobs']:
            st.write("**任務列表:**")
            
            for job_id, job_info in job_status['jobs'].items():
                with st.expander(f"📋 {job_info['name']} ({job_id})"):
                    st.write(f"**下次執行時間:** {job_info['next_run_time'] or '未排程'}")
                    st.write(f"**觸發器:** {job_info['trigger']}")
        else:
            st.info("目前沒有排程的任務")
    
    except Exception as e:
        st.error(f"取得任務狀態時發生錯誤: {e}")
    
    # 手動控制按鈕
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 啟動背景任務"):
            try:
                scheduler_manager.start_background_tasks()
                st.success("背景任務已啟動")
                st.rerun()
            except Exception as e:
                st.error(f"啟動背景任務失敗: {e}")
    
    with col2:
        if st.button("⏹️ 停止背景任務"):
            try:
                scheduler_manager.stop_all_tasks()
                st.success("背景任務已停止")
                st.rerun()
            except Exception as e:
                st.error(f"停止背景任務失敗: {e}")

def _render_notification_history(data_manager: DataManager):
    """渲染通知歷史"""
    
    st.subheader("📬 通知歷史")
    
    # 取得通知記錄
    try:
        records = data_manager.get_notification_history(limit=50)
        
        if records:
            # 統計資料
            total_notifications = len(records)
            successful_notifications = len([r for r in records if r.status == 'sent'])
            failed_notifications = len([r for r in records if r.status == 'failed'])
            
            # 顯示統計
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("總通知數", total_notifications)
            
            with col2:
                st.metric("成功發送", successful_notifications)
            
            with col3:
                st.metric("發送失敗", failed_notifications)
            
            # 成功率
            if total_notifications > 0:
                success_rate = (successful_notifications / total_notifications) * 100
                st.metric("成功率", f"{success_rate:.1f}%")
            
            # 通知記錄表格
            st.write("**最近通知記錄:**")
            
            # 篩選選項
            status_filter = st.selectbox(
                "篩選狀態",
                options=["全部", "已發送", "失敗", "待發送"],
                index=0
            )
            
            # 根據篩選條件過濾記錄
            filtered_records = records
            if status_filter != "全部":
                status_map = {"已發送": "sent", "失敗": "failed", "待發送": "pending"}
                filtered_records = [r for r in records if r.status == status_map[status_filter]]
            
            # 顯示記錄
            for record in filtered_records[:20]:  # 只顯示前20筆
                with st.expander(f"📨 {record.sent_at.strftime('%Y-%m-%d %H:%M')} - {_get_status_emoji(record.status)}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**使用者ID:** {record.user_id}")
                        st.write(f"**比賽ID:** {record.match_id}")
                        st.write(f"**狀態:** {_get_status_text(record.status)}")
                    
                    with col2:
                        st.write(f"**發送時間:** {record.sent_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**重試次數:** {record.retry_count}")
                        if record.error_message:
                            st.write(f"**錯誤訊息:** {record.error_message}")
                    
                    st.write("**通知內容:**")
                    st.text(record.message[:200] + "..." if len(record.message) > 200 else record.message)
        
        else:
            st.info("目前沒有通知記錄")
    
    except Exception as e:
        st.error(f"載入通知歷史時發生錯誤: {e}")

def _render_system_logs():
    """渲染系統日誌"""
    
    st.subheader("📝 系統日誌")
    
    try:
        # 嘗試讀取日誌檔案
        log_file_path = "logs/app.log"
        
        if st.button("🔄 重新載入日誌"):
            st.rerun()
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # 只顯示最後100行
            recent_logs = log_lines[-100:]
            
            if recent_logs:
                st.write("**最近日誌 (最後100行):**")
                
                # 日誌等級篩選
                log_level_filter = st.selectbox(
                    "篩選日誌等級",
                    options=["全部", "ERROR", "WARNING", "INFO", "DEBUG"],
                    index=0
                )
                
                # 過濾日誌
                filtered_logs = recent_logs
                if log_level_filter != "全部":
                    filtered_logs = [line for line in recent_logs if log_level_filter in line]
                
                # 顯示日誌
                log_text = "".join(filtered_logs)
                st.text_area("日誌內容", log_text, height=400)
            
            else:
                st.info("日誌檔案為空")
        
        except FileNotFoundError:
            st.warning("找不到日誌檔案")
        except Exception as e:
            st.error(f"讀取日誌檔案時發生錯誤: {e}")
    
    except Exception as e:
        st.error(f"載入系統日誌時發生錯誤: {e}")

def _get_status_emoji(status: str) -> str:
    """取得狀態對應的表情符號"""
    status_map = {
        "sent": "✅",
        "failed": "❌", 
        "pending": "⏳"
    }
    return status_map.get(status, "❓")

def _render_system_metrics():
    """渲染系統監控指標"""
    st.subheader("📈 系統監控指標")
    
    try:
        # 取得當前指標
        current_metrics = get_current_metrics()
        
        if current_metrics and current_metrics['system']:
            sys_metrics = current_metrics['system']
            
            # 系統資源使用情況
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                cpu_percent = sys_metrics['cpu_percent']
                st.metric(
                    "CPU 使用率", 
                    f"{cpu_percent:.1f}%",
                    delta=None,
                    delta_color="inverse" if cpu_percent > 80 else "normal"
                )
            
            with col2:
                memory_percent = sys_metrics['memory_percent']
                st.metric(
                    "記憶體使用率", 
                    f"{memory_percent:.1f}%",
                    delta=None,
                    delta_color="inverse" if memory_percent > 80 else "normal"
                )
            
            with col3:
                disk_percent = sys_metrics['disk_percent']
                st.metric(
                    "磁碟使用率", 
                    f"{disk_percent:.1f}%",
                    delta=None,
                    delta_color="inverse" if disk_percent > 85 else "normal"
                )
            
            with col4:
                uptime_hours = current_metrics.get('uptime_hours', 0)
                st.metric("系統運行時間", f"{uptime_hours:.1f} 小時")
            
            # 應用程式指標
            if current_metrics['application']:
                app_metrics = current_metrics['application']
                
                st.write("**應用程式指標:**")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("活躍使用者", app_metrics['active_users'])
                
                with col2:
                    st.metric("總訂閱數", app_metrics['total_subscriptions'])
                
                with col3:
                    st.metric("今日通知發送", app_metrics['notifications_sent_today'])
                
                with col4:
                    st.metric("今日通知失敗", app_metrics['notifications_failed_today'])
        
        # 健康檢查
        health_status = health_check()
        
        st.write("**系統健康狀態:**")
        
        if health_status['status'] == 'healthy':
            st.success("✅ 系統運行正常")
        elif health_status['status'] == 'warning':
            st.warning("⚠️ 系統有警告")
        elif health_status['status'] == 'critical':
            st.error("🚨 系統狀態嚴重")
        else:
            st.error("❌ 系統健康檢查失敗")
        
        # 顯示詳細檢查結果
        if 'checks' in health_status and health_status['checks']:
            with st.expander("詳細健康檢查結果"):
                for check_name, check_result in health_status['checks'].items():
                    status_icon = "✅" if check_result['status'] == 'healthy' else "⚠️" if check_result['status'] == 'warning' else "🚨"
                    st.write(f"{status_icon} **{check_name}**: {check_result}")
    
    except Exception as e:
        st.error(f"載入系統指標時發生錯誤: {e}")

def _render_error_statistics():
    """渲染錯誤統計"""
    st.subheader("🚨 錯誤統計")
    
    try:
        error_summary = error_handler.get_error_summary()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("錯誤類型數", error_summary['total_error_types'])
        
        with col2:
            st.metric("最近1小時錯誤總數", error_summary['last_hour_total'])
        
        # 顯示最近錯誤詳情
        if error_summary['recent_errors']:
            st.write("**最近錯誤詳情:**")
            
            for error_key, error_info in error_summary['recent_errors'].items():
                with st.expander(f"❌ {error_key} (發生 {error_info['count']} 次)"):
                    st.write(f"**最後發生時間:** {error_info['last_occurrence']}")
                    st.write(f"**最後錯誤訊息:** {error_info['last_error']}")
        else:
            st.success("✅ 最近1小時內沒有錯誤")
    
    except Exception as e:
        st.error(f"載入錯誤統計時發生錯誤: {e}")

def _get_status_emoji(status: str) -> str:
    """取得狀態對應的表情符號"""
    status_map = {
        "sent": "✅",
        "failed": "❌", 
        "pending": "⏳"
    }
    return status_map.get(status, "❓")

def _get_status_text(status: str) -> str:
    """取得狀態對應的中文文字"""
    status_map = {
        "sent": "已發送",
        "failed": "發送失敗",
        "pending": "待發送"
    }
    return status_map.get(status, "未知狀態")