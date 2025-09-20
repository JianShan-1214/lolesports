#!/usr/bin/env python3
"""
測試 Leaguepedia API 實作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.leaguepedia_api import LeaguepediaAPI
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_api():
    """測試 API 功能"""
    print("=== 測試 Leaguepedia API ===")
    
    api = LeaguepediaAPI()
    
    # 測試連接
    print("\n1. 測試 API 連接...")
    if api.validate_connection():
        print("✅ API 連接成功")
    else:
        print("❌ API 連接失敗")
    
    # 測試取得比賽資料
    print("\n2. 測試取得未來比賽...")
    matches = api.get_upcoming_matches(days=7)
    print(f"找到 {len(matches)} 場比賽")
    
    for i, match in enumerate(matches[:5]):  # 只顯示前5場
        print(f"  {i+1}. {match.team1.name} vs {match.team2.name}")
        print(f"     時間: {match.scheduled_time}")
        print(f"     賽事: {match.tournament}")
        print(f"     格式: {match.match_format}")
        if match.stream_url:
            print(f"     直播: {match.stream_url}")
        print()
    
    # 測試取得戰隊列表
    print("\n3. 測試取得戰隊列表...")
    teams = api.get_team_list()
    print(f"找到 {len(teams)} 個戰隊")
    
    # 按聯賽分組顯示
    leagues = {}
    for team in teams:
        league = team.league or 'Unknown'
        if league not in leagues:
            leagues[league] = []
        leagues[league].append(team.name)
    
    for league, team_names in sorted(leagues.items()):
        print(f"  {league}: {len(team_names)} 個戰隊")
        if len(team_names) <= 10:
            print(f"    {', '.join(team_names)}")
        else:
            print(f"    {', '.join(team_names[:10])}... (還有 {len(team_names)-10} 個)")

if __name__ == "__main__":
    test_api()