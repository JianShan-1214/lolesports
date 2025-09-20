"""
比賽查看頁面
顯示即將到來的 LOL 比賽資訊
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from src.models.match import Match
from src.services.leaguepedia_api import LeaguepediaAPI
from src.services.data_manager import DataManager

logger = logging.getLogger(__name__)

def render_matches_page():
    """渲染比賽查看頁面"""
    st.title("🏆 即將到來的比賽")
    st.markdown("查看最新的英雄聯盟電競比賽安排")
    
    # 初始化服務
    api = LeaguepediaAPI()
    data_manager = DataManager()
    
    # 頁面控制選項
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # 時間範圍選擇
        time_range = st.selectbox(
            "📅 選擇時間範圍",
            ["今天", "未來 3 天", "未來 7 天", "未來 14 天"],
            index=1,
            help="選擇要顯示的比賽時間範圍"
        )
    
    with col2:
        # 聯賽篩選
        league_filter = st.selectbox(
            "🏟️ 聯賽篩選",
            ["全部聯賽", "LCK", "LPL", "LEC", "LCS", "MSI", "Worlds"],
            help="篩選特定聯賽的比賽"
        )
    
    with col3:
        # 重新整理按鈕
        if st.button("🔄 重新整理", help="重新獲取最新比賽資料"):
            st.cache_data.clear()
            st.rerun()
    
    # 獲取比賽資料
    matches = get_matches_data(api, data_manager, time_range, league_filter)
    
    if not matches:
        st.info("📭 目前沒有符合條件的比賽")
        st.markdown("### 💡 提示")
        st.markdown("- 嘗試調整時間範圍或聯賽篩選")
        st.markdown("- 點擊重新整理按鈕獲取最新資料")
        return
    
    # 顯示比賽統計
    display_match_statistics(matches)
    
    # 顯示比賽列表
    display_matches_list(matches)
    
    # 顯示我的訂閱戰隊比賽
    display_my_team_matches(matches, data_manager)

@st.cache_data(ttl=300)  # 快取 5 分鐘
def get_matches_data(_api: LeaguepediaAPI, _data_manager: DataManager, time_range: str, league_filter: str) -> List[Match]:
    """獲取比賽資料（帶快取）"""
    try:
        # 計算天數
        days_map = {
            "今天": 1,
            "未來 3 天": 3,
            "未來 7 天": 7,
            "未來 14 天": 14
        }
        days = days_map.get(time_range, 3)
        
        # 從 API 獲取比賽資料
        with st.spinner("🔍 正在獲取比賽資料..."):
            matches = _api.get_upcoming_matches(days=days)
        
        # 聯賽篩選
        if league_filter != "全部聯賽":
            matches = [match for match in matches if league_filter.lower() in match.tournament.lower()]
        
        # 快取到本地資料庫
        if matches:
            _data_manager.cache_match_data(matches)
        
        logger.info(f"成功獲取 {len(matches)} 場比賽")
        return matches
        
    except Exception as e:
        logger.error(f"獲取比賽資料失敗: {e}")
        st.error(f"❌ 獲取比賽資料失敗: {e}")
        
        # 嘗試從快取獲取資料
        try:
            cached_matches = _data_manager.get_cached_matches()
            if cached_matches:
                st.warning("⚠️ 使用快取資料，可能不是最新的")
                return cached_matches
        except Exception as cache_error:
            logger.error(f"獲取快取資料失敗: {cache_error}")
        
        return []

def display_match_statistics(matches: List[Match]):
    """顯示比賽統計資訊"""
    st.markdown("### 📊 比賽統計")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總比賽數", len(matches))
    
    with col2:
        today = datetime.now().date()
        today_matches = []
        for m in matches:
            match_date = m.scheduled_time.date() if m.scheduled_time.tzinfo is None else m.scheduled_time.date()
            if match_date == today:
                today_matches.append(m)
        st.metric("今日比賽", len(today_matches))
    
    with col3:
        tournaments = set(match.tournament for match in matches)
        st.metric("聯賽數量", len(tournaments))
    
    with col4:
        now = datetime.now()
        upcoming_matches = []
        for m in matches:
            match_time = m.scheduled_time
            # 統一時區處理
            if match_time.tzinfo is not None and now.tzinfo is None:
                # 將 now 轉為 UTC 進行比較
                from datetime import timezone
                now_utc = now.replace(tzinfo=timezone.utc)
                if match_time > now_utc:
                    upcoming_matches.append(m)
            elif match_time.tzinfo is None and now.tzinfo is not None:
                # 將 match_time 轉為 UTC 進行比較
                from datetime import timezone
                match_utc = match_time.replace(tzinfo=timezone.utc)
                if match_utc > now:
                    upcoming_matches.append(m)
            else:
                # 時區一致或都沒有時區
                if match_time > now:
                    upcoming_matches.append(m)
        st.metric("即將開始", len(upcoming_matches))

def display_matches_list(matches: List[Match]):
    """顯示比賽列表"""
    st.markdown("### 📋 比賽列表")
    
    # 按日期分組顯示
    matches_by_date = {}
    for match in matches:
        # 處理時區問題
        match_time = match.scheduled_time
        if match_time.tzinfo is not None:
            # 如果有時區，轉換為本地時間的日期
            date_key = match_time.date()
        else:
            # 如果沒有時區，直接使用日期
            date_key = match_time.date()
            
        if date_key not in matches_by_date:
            matches_by_date[date_key] = []
        matches_by_date[date_key].append(match)
    
    # 按日期排序
    sorted_dates = sorted(matches_by_date.keys())
    
    for date in sorted_dates:
        date_matches = matches_by_date[date]
        
        # 日期標題
        is_today = date == datetime.now().date()
        date_str = "今天" if is_today else date.strftime("%m月%d日 (%A)")
        
        with st.expander(f"📅 {date_str} ({len(date_matches)} 場比賽)", expanded=is_today):
            for match in sorted(date_matches, key=lambda m: m.scheduled_time.replace(tzinfo=None) if m.scheduled_time.tzinfo else m.scheduled_time):
                display_match_card(match)

def display_match_card(match: Match):
    """顯示單場比賽卡片"""
    from datetime import timezone, timedelta
    
    # 計算比賽狀態
    now = datetime.now()
    match_time = match.scheduled_time
    
    # 確保時區一致性
    if match_time.tzinfo is not None and now.tzinfo is None:
        # match_time 有時區，now 沒有，將 now 設為 UTC
        now = now.replace(tzinfo=timezone.utc)
    elif match_time.tzinfo is None and now.tzinfo is not None:
        # now 有時區，match_time 沒有，將 match_time 設為 UTC
        match_time = match_time.replace(tzinfo=timezone.utc)
    elif match_time.tzinfo is None and now.tzinfo is None:
        # 都沒有時區，保持原樣
        pass
    
    time_diff = match_time - now
    
    if time_diff.total_seconds() > 0:
        if time_diff.total_seconds() < 3600:  # 1小時內
            status_color = "🔴"
            status_text = f"即將開始 ({int(time_diff.total_seconds() / 60)} 分鐘後)"
        elif time_diff.total_seconds() < 86400:  # 24小時內
            status_color = "🟡"
            hours = int(time_diff.total_seconds() / 3600)
            status_text = f"{hours} 小時後開始"
        else:
            status_color = "🟢"
            days = time_diff.days
            status_text = f"{days} 天後開始"
    else:
        status_color = "⚫"
        status_text = "比賽已開始或結束"
    
    # 比賽卡片
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 3])
        
        with col1:
            st.markdown(f"**{match.team1.name}**")
            st.caption(f"{match.team1.region} - {match.team1.league}")
        
        with col2:
            st.markdown(f"<div style='text-align: center;'>", unsafe_allow_html=True)
            st.markdown("**VS**")
            st.markdown(f"{match.match_format}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"**{match.team2.name}**")
            st.caption(f"{match.team2.region} - {match.team2.league}")
        
        # 比賽詳情
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.caption(f"🏟️ {match.tournament}")
            # 顯示台灣時間
            if match.scheduled_time.tzinfo is not None:
                # 如果有時區資訊，直接顯示
                taiwan_time = match.scheduled_time
            else:
                # 如果沒有時區資訊，假設已經是台灣時間
                taiwan_time = match.scheduled_time
            st.caption(f"⏰ {taiwan_time.strftime('%m/%d %H:%M')} (台灣時間)")
        
        with col_info2:
            st.caption(f"{status_color} {status_text}")
            if match.stream_url:
                st.markdown(f"[📺 觀看直播]({match.stream_url})")
        
        st.divider()

def display_my_team_matches(matches: List[Match], data_manager: DataManager):
    """顯示我訂閱戰隊的比賽"""
    st.markdown("### ⭐ 我的戰隊比賽")
    
    # 獲取用戶輸入的 Telegram ID（簡化版本）
    user_id = st.text_input(
        "輸入您的 Telegram ID 查看訂閱戰隊比賽",
        placeholder="例如: @username 或 123456789",
        help="輸入您的 Telegram 用戶名或 ID"
    )
    
    if not user_id:
        st.info("💡 輸入您的 Telegram ID 來查看訂閱戰隊的比賽")
        return
    
    try:
        # 獲取用戶訂閱
        subscription = data_manager.get_user_subscription(user_id)
        
        if not subscription or not subscription.subscribed_teams:
            st.info("📭 您還沒有訂閱任何戰隊")
            st.markdown("前往 **戰隊訂閱** 頁面來訂閱您喜歡的戰隊！")
            return
        
        # 篩選訂閱戰隊的比賽
        my_matches = []
        for match in matches:
            if (match.team1.name in subscription.subscribed_teams or 
                match.team2.name in subscription.subscribed_teams):
                my_matches.append(match)
        
        if not my_matches:
            st.info("📭 您訂閱的戰隊近期沒有比賽")
            st.markdown(f"**您訂閱的戰隊:** {', '.join(subscription.subscribed_teams)}")
            return
        
        st.success(f"🎉 找到 {len(my_matches)} 場您訂閱戰隊的比賽！")
        
        # 顯示訂閱戰隊比賽
        for match in sorted(my_matches, key=lambda m: m.scheduled_time):
            # 高亮顯示訂閱的戰隊
            team1_highlight = "**🌟 " if match.team1.name in subscription.subscribed_teams else ""
            team2_highlight = "**🌟 " if match.team2.name in subscription.subscribed_teams else ""
            
            with st.container():
                st.markdown(f"### {team1_highlight}{match.team1.name}{'**' if team1_highlight else ''} vs {team2_highlight}{match.team2.name}{'**' if team2_highlight else ''}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"🏟️ {match.tournament}")
                    # 顯示台灣時間
                    if match.scheduled_time.tzinfo is not None:
                        taiwan_time = match.scheduled_time
                    else:
                        taiwan_time = match.scheduled_time
                    st.caption(f"⏰ {taiwan_time.strftime('%m/%d %H:%M')} (台灣時間)")
                
                with col2:
                    st.caption(f"📊 {match.match_format}")
                    if match.stream_url:
                        st.markdown(f"[📺 觀看直播]({match.stream_url})")
                
                st.divider()
        
    except Exception as e:
        logger.error(f"獲取用戶訂閱失敗: {e}")
        st.error(f"❌ 獲取訂閱資訊失敗: {e}")