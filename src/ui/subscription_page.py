"""
戰隊訂閱頁面
處理使用者戰隊訂閱功能
"""

import streamlit as st
from typing import List

from ..services import DataManager, LeaguepediaAPI
from ..models import UserSubscription, Team

def render_subscription_page():
    """渲染戰隊訂閱頁面"""
    st.title("🎮 戰隊訂閱")
    st.markdown("選擇您想要接收比賽通知的戰隊")
    
    # 初始化服務
    data_manager = DataManager()
    leaguepedia_api = LeaguepediaAPI()
    
    # 載入戰隊列表
    if 'teams' not in st.session_state:
        with st.spinner("載入戰隊列表中..."):
            st.session_state.teams = leaguepedia_api.get_team_list()
    
    teams = st.session_state.teams
    
    if not teams:
        st.error("無法載入戰隊列表，請稍後再試")
        return
    
    # 使用者輸入區域
    st.subheader("📝 訂閱設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        telegram_user_id = st.text_input(
            "Telegram 使用者 ID",
            help="請輸入您的Telegram使用者ID，可以透過@userinfobot取得"
        )
    
    with col2:
        telegram_username = st.text_input(
            "Telegram 使用者名稱",
            help="請輸入您的Telegram使用者名稱（選填）"
        )
    
    # 戰隊選擇
    st.subheader("⚔️ 選擇戰隊")
    
    # 按地區分組顯示戰隊
    regions = list(set(team.region for team in teams if team.region))
    regions.sort()
    
    selected_teams = []
    
    if regions:
        # 地區篩選
        selected_region = st.selectbox("選擇地區", ["全部"] + regions)
        
        # 根據選擇的地區篩選戰隊
        if selected_region == "全部":
            filtered_teams = teams
        else:
            filtered_teams = [team for team in teams if team.region == selected_region]
        
        # 戰隊選擇
        team_options = [f"{team.name} - {team.league}" for team in filtered_teams]
        team_names = [team.name for team in filtered_teams]
        
        selected_indices = st.multiselect(
            "選擇要訂閱的戰隊",
            options=range(len(team_options)),
            format_func=lambda x: team_options[x],
            help="可以選擇多個戰隊"
        )
        
        selected_teams = [team_names[i] for i in selected_indices]
    
    # 顯示選擇的戰隊
    if selected_teams:
        st.subheader("✅ 已選擇的戰隊")
        for team in selected_teams:
            st.write(f"• {team}")
    
    # 提交按鈕
    if st.button("💾 儲存訂閱", type="primary"):
        if not telegram_user_id:
            st.error("請輸入Telegram使用者ID")
        elif not selected_teams:
            st.error("請至少選擇一個戰隊")
        else:
            # 建立或更新訂閱
            subscription = UserSubscription(
                user_id=telegram_user_id,
                telegram_username=telegram_username or telegram_user_id,
                subscribed_teams=selected_teams
            )
            
            success = data_manager.save_subscription(subscription)
            
            if success:
                st.success(f"✅ 成功訂閱 {len(selected_teams)} 個戰隊！")
                st.balloons()
                
                # 顯示訂閱摘要
                st.info(
                    f"📱 Telegram ID: {telegram_user_id}\n\n"
                    f"⚔️ 訂閱戰隊: {', '.join(selected_teams)}\n\n"
                    f"🔔 您將在這些戰隊有比賽時收到通知"
                )
            else:
                st.error("❌ 儲存訂閱失敗，請稍後再試")
    
    # 顯示使用說明
    with st.expander("📖 使用說明"):
        st.markdown("""
        ### 如何取得Telegram使用者ID？
        
        1. 在Telegram中搜尋 `@userinfobot`
        2. 點擊開始對話
        3. 機器人會回覆您的使用者ID
        4. 將ID複製到上方的輸入框中
        
        ### 注意事項
        
        - 請確保您的Telegram使用者ID正確
        - 系統會在比賽開始前1小時發送通知
        - 您可以隨時修改或取消訂閱
        - 通知訊息將包含比賽時間、戰隊和賽事資訊
        """)

def _load_user_subscription(data_manager: DataManager, user_id: str) -> UserSubscription:
    """載入使用者現有訂閱"""
    subscription = data_manager.get_user_subscription(user_id)
    if subscription:
        return subscription
    else:
        return UserSubscription(
            user_id=user_id,
            telegram_username=user_id,
            subscribed_teams=[]
        )