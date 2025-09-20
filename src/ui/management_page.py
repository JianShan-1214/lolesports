"""
訂閱管理頁面
處理使用者訂閱管理功能
"""

import streamlit as st
from typing import Optional

from ..services import DataManager, NotificationManager
from ..models import UserSubscription

def render_management_page():
    """渲染訂閱管理頁面"""
    st.title("⚙️ 訂閱管理")
    st.markdown("管理您的戰隊訂閱和通知設定")
    
    # 初始化服務
    data_manager = DataManager()
    notification_manager = NotificationManager()
    
    # 使用者ID輸入
    st.subheader("🔍 查詢訂閱")
    user_id = st.text_input(
        "輸入Telegram使用者ID",
        help="輸入您的Telegram使用者ID來查詢和管理訂閱"
    )
    
    if user_id:
        # 查詢使用者訂閱
        subscription = data_manager.get_user_subscription(user_id)
        
        if subscription:
            _render_subscription_management(subscription, data_manager, notification_manager)
        else:
            st.warning("找不到此使用者的訂閱記錄")
            st.info("請先到「戰隊訂閱」頁面建立訂閱")
    
    # 顯示所有訂閱統計
    _render_subscription_statistics(data_manager)

def _render_subscription_management(
    subscription: UserSubscription, 
    data_manager: DataManager,
    notification_manager: NotificationManager
):
    """渲染訂閱管理介面"""
    
    st.subheader("📋 當前訂閱")
    
    # 顯示基本資訊
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("使用者ID", subscription.user_id)
        st.metric("使用者名稱", subscription.telegram_username)
    
    with col2:
        st.metric("訂閱戰隊數量", len(subscription.subscribed_teams))
        st.metric("訂閱狀態", "啟用" if subscription.is_active else "停用")
    
    # 顯示訂閱的戰隊
    if subscription.subscribed_teams:
        st.subheader("⚔️ 訂閱戰隊")
        
        # 使用可編輯的多選框
        available_teams = subscription.subscribed_teams.copy()
        
        # 戰隊管理
        teams_to_remove = st.multiselect(
            "選擇要取消訂閱的戰隊",
            options=subscription.subscribed_teams,
            help="選擇您想要取消訂閱的戰隊"
        )
        
        # 新增戰隊輸入
        new_team = st.text_input(
            "新增戰隊",
            help="輸入新戰隊名稱來新增訂閱"
        )
        
        # 操作按鈕
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("➕ 新增戰隊"):
                if new_team and new_team not in subscription.subscribed_teams:
                    subscription.add_team(new_team)
                    success = data_manager.save_subscription(subscription)
                    if success:
                        st.success(f"成功新增戰隊: {new_team}")
                        st.rerun()
                    else:
                        st.error("新增戰隊失敗")
                elif new_team in subscription.subscribed_teams:
                    st.warning("此戰隊已在訂閱列表中")
                else:
                    st.warning("請輸入戰隊名稱")
        
        with col2:
            if st.button("➖ 移除選中戰隊"):
                if teams_to_remove:
                    for team in teams_to_remove:
                        subscription.remove_team(team)
                    
                    success = data_manager.save_subscription(subscription)
                    if success:
                        st.success(f"成功移除 {len(teams_to_remove)} 個戰隊")
                        st.rerun()
                    else:
                        st.error("移除戰隊失敗")
                else:
                    st.warning("請選擇要移除的戰隊")
        
        with col3:
            if st.button("🧪 發送測試通知"):
                success = notification_manager.send_test_notification(subscription.user_id)
                if success:
                    st.success("測試通知已發送！")
                else:
                    st.error("發送測試通知失敗")
        
        with col4:
            if st.button("🗑️ 刪除訂閱", type="secondary"):
                if st.session_state.get('confirm_delete', False):
                    success = data_manager.delete_subscription(subscription.user_id)
                    if success:
                        st.success("訂閱已刪除")
                        st.session_state.confirm_delete = False
                        st.rerun()
                    else:
                        st.error("刪除訂閱失敗")
                else:
                    st.session_state.confirm_delete = True
                    st.warning("再次點擊確認刪除")
        
        # 顯示當前訂閱列表
        st.subheader("📝 當前訂閱列表")
        for i, team in enumerate(subscription.subscribed_teams, 1):
            st.write(f"{i}. {team}")
    
    else:
        st.info("目前沒有訂閱任何戰隊")
    
    # 顯示訂閱歷史
    st.subheader("📊 訂閱資訊")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.write(f"**建立時間:** {subscription.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    with info_col2:
        st.write(f"**最後更新:** {subscription.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

def _render_subscription_statistics(data_manager: DataManager):
    """渲染訂閱統計資訊"""
    
    st.subheader("📈 系統統計")
    
    try:
        # 取得所有訂閱
        all_subscriptions = data_manager.get_all_subscriptions()
        
        # 計算統計資料
        total_users = len(all_subscriptions)
        total_team_subscriptions = sum(len(sub.subscribed_teams) for sub in all_subscriptions)
        
        # 統計最受歡迎的戰隊
        team_counts = {}
        for subscription in all_subscriptions:
            for team in subscription.subscribed_teams:
                team_counts[team] = team_counts.get(team, 0) + 1
        
        # 顯示統計資料
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("總使用者數", total_users)
        
        with col2:
            st.metric("總訂閱數", total_team_subscriptions)
        
        with col3:
            avg_subscriptions = total_team_subscriptions / total_users if total_users > 0 else 0
            st.metric("平均每人訂閱", f"{avg_subscriptions:.1f}")
        
        # 顯示熱門戰隊
        if team_counts:
            st.subheader("🏆 熱門戰隊")
            
            # 排序並顯示前10名
            sorted_teams = sorted(team_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            for i, (team, count) in enumerate(sorted_teams, 1):
                st.write(f"{i}. **{team}** - {count} 人訂閱")
    
    except Exception as e:
        st.error(f"載入統計資料時發生錯誤: {e}")