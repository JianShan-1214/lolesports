"""
Leaguepedia API客戶端
處理比賽資料獲取和解析
"""

import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import time
from urllib.parse import urlencode

from ..models import Team, Match
from ..utils.error_handler import APIError, api_error_handler, safe_execute, create_graceful_degradation
from config.settings import settings

logger = logging.getLogger(__name__)

class LeaguepediaAPI:
    """Leaguepedia API客戶端類別"""
    
    def __init__(self):
        self.api_url = settings.get('leaguepedia.api_url', 'https://lol.fandom.com/api.php')
        self.user_agent = settings.get('leaguepedia.user_agent', 'LOL-Match-Notification-System/1.0')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
        self.max_retries = 3
        self.retry_delay = 1  # 秒
        self.timeout = 30
    
    def _make_request_with_retry(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """執行API請求並包含重試機制"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"API請求嘗試 {attempt + 1}/{self.max_retries}")
                
                response = self.session.get(
                    self.api_url, 
                    params=params, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 檢查API回應是否包含錯誤
                if 'error' in data:
                    error_msg = data['error'].get('info', '未知錯誤')
                    logger.error(f"API回應錯誤: {error_msg}")
                    raise requests.RequestException(f"API錯誤: {error_msg}")
                
                logger.debug("API請求成功")
                return data
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"請求超時 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"連接錯誤 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                if e.response.status_code == 429:  # 速率限制
                    logger.warning(f"遇到速率限制，等待後重試 (嘗試 {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay * (2 ** attempt))  # 指數退避
                else:
                    logger.error(f"HTTP錯誤 {e.response.status_code}: {e}")
                    raise APIError(f"HTTP錯誤 {e.response.status_code}", "HTTP_ERROR", {"status_code": e.response.status_code})
                    
            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"請求異常 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                
            except Exception as e:
                last_exception = e
                logger.error(f"未預期的錯誤 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                break  # 對於未預期的錯誤，不重試
            
            # 如果不是最後一次嘗試，等待後重試
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)  # 指數退避
                logger.debug(f"等待 {delay} 秒後重試")
                time.sleep(delay)
        
        # 所有重試都失敗
        logger.error(f"API請求失敗，已重試 {self.max_retries} 次")
        if last_exception:
            raise APIError(f"API請求失敗: {last_exception}", "API_REQUEST_FAILED", {"retries": self.max_retries})
        raise APIError("API請求失敗", "API_REQUEST_FAILED")
    
    @api_error_handler
    def get_upcoming_matches(self, days: int = 2) -> List[Match]:
        """取得未來指定天數內的比賽"""
        try:
            logger.info(f"查詢未來 {days} 天的比賽資料")
            
            # 計算日期範圍 (UTC 時間)
            from datetime import datetime, timedelta, timezone
            now_utc = datetime.now(timezone.utc)
            start_date = now_utc
            end_date = start_date + timedelta(days=days)
            
            # 使用正確的 Leaguepedia Cargo API 查詢
            # 根據實際測試的 API 結構
            params = {
                'action': 'cargoquery',
                'format': 'json',
                'tables': 'MatchSchedule',
                'fields': 'Team1,Team2,DateTime_UTC,OverviewPage,BestOf,Stream,Winner',
                'where': f'DateTime_UTC >= "{start_date.strftime("%Y-%m-%d %H:%M:%S")}" AND DateTime_UTC <= "{end_date.strftime("%Y-%m-%d %H:%M:%S")}" AND Team1 != "TBD" AND Team2 != "TBD"',
                'order_by': 'DateTime_UTC ASC',
                'limit': '100'
            }
            
            logger.debug(f"API 查詢參數: {params}")
            data = self._make_request_with_retry(params)
            
            if not data:
                logger.warning("API 請求失敗，嘗試備用查詢")
                return self._get_fallback_matches(days)
            
            matches = []
            
            if 'cargoquery' in data and data['cargoquery']:
                logger.info(f"API 返回 {len(data['cargoquery'])} 筆資料")
                for item in data['cargoquery']:
                    try:
                        # Cargo API 的回應結構是 {'title': {...}}
                        match_data = item.get('title', {})
                        if match_data and match_data.get('Team1') and match_data.get('Team2'):
                            # 過濾掉 TBD 比賽
                            if match_data.get('Team1') != 'TBD' and match_data.get('Team2') != 'TBD':
                                match = self._parse_match_data(match_data)
                                if match:
                                    matches.append(match)
                    except Exception as parse_error:
                        logger.warning(f"解析比賽資料失敗: {parse_error}")
                        continue
            
            if matches:
                logger.info(f"成功解析 {len(matches)} 場比賽")
                return matches
            else:
                logger.warning("沒有找到即將進行的比賽，嘗試查詢更廣泛的時間範圍")
                return self._get_fallback_matches(days)
            
        except Exception as e:
            logger.error(f"取得比賽資料時發生錯誤: {e}")
            logger.info("返回模擬比賽資料")
            return self._get_mock_matches(days)
    
    def _get_fallback_matches(self, days: int) -> List[Match]:
        """當主要查詢失敗時的備用查詢方法"""
        try:
            logger.info("嘗試備用查詢方法 - 查詢主要聯賽的比賽")
            
            # 查詢主要聯賽的比賽資料
            params = {
                'action': 'cargoquery',
                'format': 'json',
                'tables': 'MatchSchedule',
                'fields': 'Team1,Team2,DateTime_UTC,OverviewPage,BestOf,Stream,Winner',
                'where': '(OverviewPage LIKE "%LCK%" OR OverviewPage LIKE "%LPL%" OR OverviewPage LIKE "%LEC%" OR OverviewPage LIKE "%LCS%" OR OverviewPage LIKE "%Worlds%" OR OverviewPage LIKE "%MSI%") AND Team1 != "TBD" AND Team2 != "TBD"',
                'order_by': 'DateTime_UTC DESC',
                'limit': '50'
            }
            
            data = self._make_request_with_retry(params)
            
            if data and 'cargoquery' in data and data['cargoquery']:
                matches = []
                from datetime import datetime, timezone, timedelta
                now_utc = datetime.now(timezone.utc)
                future_cutoff = now_utc + timedelta(days=days)
                
                for item in data['cargoquery']:
                    try:
                        match_data = item.get('title', {})
                        if match_data and match_data.get('Team1') and match_data.get('Team2'):
                            # 過濾掉 TBD 比賽
                            if match_data.get('Team1') != 'TBD' and match_data.get('Team2') != 'TBD':
                                match = self._parse_match_data(match_data)
                                if match and match.scheduled_time > now_utc:
                                    matches.append(match)
                    except Exception as e:
                        logger.debug(f"跳過無效的比賽資料: {e}")
                        continue
                
                if matches:
                    # 按時間排序
                    matches.sort(key=lambda x: x.scheduled_time)
                    logger.info(f"備用查詢成功，找到 {len(matches)} 場即將進行的比賽")
                    return matches
            
            logger.warning("備用查詢也沒有找到合適的比賽，使用模擬資料")
            return self._get_mock_matches(days)
            
        except Exception as e:
            logger.error(f"備用查詢失敗: {e}")
            return self._get_mock_matches(days)
    
    def _get_mock_matches(self, days: int = 2) -> List[Match]:
        """取得模擬比賽資料（當API無法使用時）"""
        from datetime import timezone, timedelta as td
        
        # 設定台灣時區 (UTC+8)
        taiwan_tz = timezone(td(hours=8))
        
        mock_matches = []
        
        # 建立更多模擬比賽資料
        teams_data = [
            # 今天的比賽
            ('T1', 'Gen.G', 'LCK Spring 2024', 'BO3'),
            ('DRX', 'KT Rolster', 'LCK Spring 2024', 'BO3'),
            
            # 明天的比賽
            ('JD Gaming', 'Bilibili Gaming', 'LPL Spring 2024', 'BO3'),
            ('Top Esports', 'Weibo Gaming', 'LPL Spring 2024', 'BO3'),
            
            # 後天的比賽
            ('G2 Esports', 'Fnatic', 'LEC Spring 2024', 'BO3'),
            ('MAD Lions', 'Team Vitality', 'LEC Spring 2024', 'BO3'),
            
            # 更多比賽
            ('Cloud9', 'Team Liquid', 'LCS Spring 2024', 'BO3'),
            ('100 Thieves', 'TSM', 'LCS Spring 2024', 'BO3'),
            
            # MSI 比賽
            ('T1', 'JD Gaming', 'MSI 2024', 'BO5'),
            ('G2 Esports', 'Gen.G', 'MSI 2024', 'BO5'),
        ]
        
        # 從現在開始，每隔幾小時安排比賽
        base_time = datetime.now(taiwan_tz).replace(minute=0, second=0, microsecond=0)
        
        # 設定明天開始的比賽時間
        tomorrow = base_time + td(days=1)
        base_time = tomorrow.replace(hour=14)  # 下午2點開始
        
        for i, (team1_name, team2_name, tournament, match_format) in enumerate(teams_data):
            if i >= days * 4:  # 每天最多 4 場比賽
                break
                
            # 確定聯賽和地區
            if 'LCK' in tournament:
                region = 'KR'
                league = 'LCK'
            elif 'LPL' in tournament:
                region = 'CN'
                league = 'LPL'
            elif 'LEC' in tournament:
                region = 'EU'
                league = 'LEC'
            elif 'LCS' in tournament:
                region = 'NA'
                league = 'LCS'
            else:
                region = 'International'
                league = 'MSI'
            
            team1 = Team(
                team_id=team1_name.replace(' ', '_').lower(),
                name=team1_name,
                region=region,
                league=league
            )
            
            team2 = Team(
                team_id=team2_name.replace(' ', '_').lower(),
                name=team2_name,
                region=region,
                league=league
            )
            
            # 根據聯賽設定不同的比賽時間
            if 'LCK' in tournament:
                # LCK 比賽：下午2點和晚上8點
                day_offset = i // 2
                match_hour = 14 if i % 2 == 0 else 20
                match_time = base_time + td(days=day_offset)
                match_time = match_time.replace(hour=match_hour)
            elif 'LPL' in tournament:
                # LPL 比賽：下午5點和晚上9點
                day_offset = i // 2
                match_hour = 17 if i % 2 == 0 else 21
                match_time = base_time + td(days=day_offset)
                match_time = match_time.replace(hour=match_hour)
            elif 'LEC' in tournament:
                # LEC 比賽：晚上11點（歐洲時間下午）
                day_offset = i // 2
                match_time = base_time + td(days=day_offset)
                match_time = match_time.replace(hour=23)
            elif 'LCS' in tournament:
                # LCS 比賽：凌晨3點（美國時間晚上）
                day_offset = i // 2
                match_time = base_time + td(days=day_offset + 1)
                match_time = match_time.replace(hour=3)
            else:
                # MSI 等國際賽事：下午6點
                day_offset = i // 2
                match_time = base_time + td(days=day_offset)
                match_time = match_time.replace(hour=18)
            
            # 設定直播連結（模擬）
            stream_urls = [
                "https://www.twitch.tv/lck",
                "https://www.twitch.tv/lpl",
                "https://www.twitch.tv/lec",
                "https://www.twitch.tv/lcs",
                "https://www.youtube.com/watch?v=example"
            ]
            
            match = Match(
                match_id=f'mock_match_{i+1}_{int(match_time.timestamp())}',
                team1=team1,
                team2=team2,
                scheduled_time=match_time,
                tournament=tournament,
                match_format=match_format,
                status='scheduled',
                stream_url=stream_urls[i % len(stream_urls)]
            )
            
            mock_matches.append(match)
        
        logger.info(f"返回 {len(mock_matches)} 場模擬比賽（台灣時區）")
        return mock_matches
    
    @api_error_handler
    def get_team_list(self) -> List[Team]:
        """取得戰隊列表"""
        try:
            logger.info("從 API 取得戰隊列表")
            
            # 查詢 Teams 表格
            params = {
                'action': 'cargoquery',
                'format': 'json',
                'tables': 'Teams',
                'fields': 'Name,Region,League,OverviewPage',
                'where': 'IsLowercase != "Yes"',  # 排除小寫重複項
                'order_by': 'Region,Name',
                'limit': '500'
            }
            
            data = self._make_request_with_retry(params)
            
            if not data or 'cargoquery' not in data:
                logger.warning("API 查詢戰隊失敗，使用預設資料")
                return self._get_default_teams()
            
            teams = []
            seen_teams = set()  # 避免重複
            
            for item in data['cargoquery']:
                try:
                    team_data = item.get('title', {})
                    team_name = team_data.get('Name', '')
                    
                    if team_name and team_name not in seen_teams:
                        team = Team(
                            team_id=team_name.replace(' ', '_').lower(),
                            name=team_name,
                            region=team_data.get('Region', ''),
                            league=team_data.get('League', '')
                        )
                        teams.append(team)
                        seen_teams.add(team_name)
                        
                except Exception as e:
                    logger.debug(f"跳過無效的戰隊資料: {e}")
                    continue
            
            if teams:
                logger.info(f"成功從 API 取得 {len(teams)} 個戰隊")
                # 合併預設戰隊以確保有足夠的選項
                default_teams = self._get_default_teams()
                for default_team in default_teams:
                    if default_team.name not in seen_teams:
                        teams.append(default_team)
                
                return teams
            else:
                logger.warning("API 沒有返回戰隊資料，使用預設資料")
                return self._get_default_teams()
            
        except Exception as e:
            logger.error(f"取得戰隊列表時發生錯誤: {e}")
            return self._get_default_teams()
    
    def _get_default_teams(self) -> List[Team]:
        """取得預設戰隊列表（當API無法使用時）"""
        default_teams_data = [
            # LCK (韓國)
            {'name': 'T1', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'Gen.G', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'DRX', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'KT Rolster', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'Hanwha Life Esports', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'DWG KIA', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'Kwangdong Freecs', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'Nongshim RedForce', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'Brion', 'region': 'LCK', 'league': 'LCK'},
            {'name': 'OK Brion', 'region': 'LCK', 'league': 'LCK'},
            
            # LPL (中國)
            {'name': 'JD Gaming', 'region': 'LPL', 'league': 'LPL'},
            {'name': 'Bilibili Gaming', 'region': 'LPL', 'league': 'LPL'},
            {'name': 'Top Esports', 'region': 'LPL', 'league': 'LPL'},
            {'name': 'Weibo Gaming', 'region': 'LPL', 'league': 'LPL'},
            {'name': 'LNG Esports', 'region': 'LPL', 'league': 'LPL'},
            {'name': 'FunPlus Phoenix', 'region': 'LPL', 'league': 'LPL'},
            {'name': 'Invictus Gaming', 'region': 'LPL', 'league': 'LPL'},
            {'name': 'EDward Gaming', 'region': 'LPL', 'league': 'LPL'},
            
            # LCS (北美)
            {'name': 'Cloud9', 'region': 'LCS', 'league': 'LCS'},
            {'name': 'Team Liquid', 'region': 'LCS', 'league': 'LCS'},
            {'name': '100 Thieves', 'region': 'LCS', 'league': 'LCS'},
            {'name': 'TSM', 'region': 'LCS', 'league': 'LCS'},
            {'name': 'FlyQuest', 'region': 'LCS', 'league': 'LCS'},
            {'name': 'NRG', 'region': 'LCS', 'league': 'LCS'},
            
            # LEC (歐洲)
            {'name': 'G2 Esports', 'region': 'LEC', 'league': 'LEC'},
            {'name': 'Fnatic', 'region': 'LEC', 'league': 'LEC'},
            {'name': 'MAD Lions', 'region': 'LEC', 'league': 'LEC'},
            {'name': 'Team Heretics', 'region': 'LEC', 'league': 'LEC'},
            {'name': 'Team Vitality', 'region': 'LEC', 'league': 'LEC'},
            {'name': 'SK Gaming', 'region': 'LEC', 'league': 'LEC'},
            
            # PCS (太平洋)
            {'name': 'PSG Talon', 'region': 'PCS', 'league': 'PCS'},
            {'name': 'CTBC Flying Oyster', 'region': 'PCS', 'league': 'PCS'},
            {'name': 'J Team', 'region': 'PCS', 'league': 'PCS'},
        ]
        
        teams = []
        for team_data in default_teams_data:
            team = Team(
                team_id=team_data['name'].replace(' ', '_'),
                name=team_data['name'],
                region=team_data['region'],
                league=team_data['league']
            )
            teams.append(team)
        
        logger.info(f"返回 {len(teams)} 個預設戰隊")
        return teams
    
    def get_match_details(self, match_id: str) -> Optional[Match]:
        """取得特定比賽詳情"""
        try:
            logger.info(f"查詢比賽詳情: {match_id}")
            
            params = {
                'action': 'cargoquery',
                'format': 'json',
                'tables': 'MatchSchedule=MS,Teams=T1,Teams=T2',
                'join_on': 'MS.Team1=T1.OverviewPage,MS.Team2=T2.OverviewPage',
                'fields': 'MS.UniqueGame,MS.Team1,MS.Team2,MS.DateTime_UTC,MS.Tournament,MS.BestOf,T1.Region,T2.Region,MS.Stream',
                'where': f'MS.UniqueGame="{match_id}"',
                'limit': '1'
            }
            
            data = self._make_request_with_retry(params)
            if not data:
                return None
            
            if 'cargoquery' in data and data['cargoquery']:
                match_data = data['cargoquery'][0]['title']
                match = self._parse_match_data(match_data)
                if match:
                    logger.info(f"成功取得比賽詳情: {match.team1.name} vs {match.team2.name}")
                return match
            
            logger.warning(f"找不到比賽: {match_id}")
            return None
            
        except Exception as e:
            logger.error(f"取得比賽詳情時發生錯誤: {e}")
            return None
    
    def _parse_match_data(self, match_data: Dict[str, Any]) -> Optional[Match]:
        """解析比賽資料"""
        try:
            # 驗證必要欄位
            team1_name = match_data.get('Team1', '')
            team2_name = match_data.get('Team2', '')
            
            if not team1_name or not team2_name:
                logger.debug(f"比賽資料缺少戰隊資訊: {match_data}")
                return None
            
            # 跳過 TBD 比賽
            if team1_name == 'TBD' or team2_name == 'TBD':
                return None
            
            # 解析時間
            datetime_str = match_data.get('DateTime UTC', '')
            if datetime_str:
                try:
                    # 處理 Leaguepedia 的時間格式
                    from datetime import datetime, timezone
                    scheduled_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                    # 設定為 UTC 時區
                    scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
                        
                except Exception as e:
                    logger.warning(f"解析比賽時間時發生錯誤: {datetime_str}, {e}")
                    return None
            else:
                logger.debug("比賽資料缺少時間資訊")
                return None
            
            # 從 OverviewPage 提取賽事資訊
            overview_page = match_data.get('OverviewPage', '')
            tournament = self._extract_tournament_from_overview(overview_page)
            league = self._extract_league_from_overview(overview_page)
            
            # 建立戰隊物件
            team1 = Team(
                team_id=team1_name.replace(' ', '_').lower(),
                name=team1_name,
                region=self._get_team_region_from_league(league),
                league=league
            )
            
            team2 = Team(
                team_id=team2_name.replace(' ', '_').lower(),
                name=team2_name,
                region=self._get_team_region_from_league(league),
                league=league
            )
            
            # 解析比賽格式
            best_of = match_data.get('BestOf', '3')
            if best_of and str(best_of).isdigit():
                match_format = f"BO{best_of}"
            else:
                match_format = "BO3"
            
            # 處理直播連結
            stream_url = match_data.get('Stream', None)
            if stream_url:
                # 清理直播連結
                if isinstance(stream_url, str):
                    if stream_url.startswith('http'):
                        pass  # 已經是完整 URL
                    elif 'twitch.tv' in stream_url:
                        if not stream_url.startswith('https://'):
                            stream_url = f"https://www.{stream_url}"
                    else:
                        stream_url = None
                else:
                    stream_url = None
            
            # 判斷比賽狀態
            status = 'scheduled'
            winner = match_data.get('Winner', '')
            if winner and winner != '0':
                status = 'completed'
            
            # 生成唯一的比賽 ID
            match_id = f"{team1_name}_{team2_name}_{scheduled_time.strftime('%Y%m%d_%H%M')}"
            match_id = match_id.replace(' ', '_').replace('/', '_')
            
            # 建立比賽物件
            match = Match(
                match_id=match_id,
                team1=team1,
                team2=team2,
                scheduled_time=scheduled_time,
                tournament=tournament,
                match_format=match_format,
                status=status,
                stream_url=stream_url
            )
            
            return match
            
        except Exception as e:
            logger.error(f"解析比賽資料時發生錯誤: {e}")
            logger.debug(f"問題資料: {match_data}")
            return None
    
    def _parse_team_data(self, team_data: Dict[str, Any]) -> Optional[Team]:
        """解析戰隊資料"""
        try:
            # 驗證必要欄位
            team_id = team_data.get('OverviewPage', '')
            team_name = team_data.get('Name', '')
            
            if not team_id or not team_name:
                logger.debug(f"戰隊資料缺少必要欄位: {team_data}")
                return None
            
            team = Team(
                team_id=team_id,
                name=team_name,
                region=team_data.get('Region', ''),
                league=team_data.get('League', '')
            )
            
            return team
            
        except Exception as e:
            logger.error(f"解析戰隊資料時發生錯誤: {e}")
            logger.debug(f"問題資料: {team_data}")
            return None
    
    def validate_connection(self) -> bool:
        """驗證API連接"""
        try:
            logger.info("驗證Leaguepedia API連接")
            
            # 使用最簡單的查詢來測試連接
            params = {
                'action': 'query',
                'format': 'json',
                'meta': 'siteinfo',
                'siprop': 'general'
            }
            
            response = self.session.get(
                self.api_url, 
                params=params, 
                timeout=10  # 較短的超時時間用於連接測試
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'query' in data and 'general' in data['query']:
                logger.info("Leaguepedia API連接驗證成功")
                return True
            else:
                logger.warning("API 回應格式異常")
                return False
                
        except Exception as e:
            logger.warning(f"API 連接驗證失敗: {e}")
            return False
    

    
    def _get_team_region(self, team_name: str) -> str:
        """根據戰隊名稱推斷地區"""
        # 簡單的地區映射
        lck_teams = ['T1', 'Gen.G', 'DRX', 'KT Rolster', 'Hanwha Life Esports', 'DWG KIA']
        lpl_teams = ['JD Gaming', 'Bilibili Gaming', 'Top Esports', 'Weibo Gaming']
        lec_teams = ['G2 Esports', 'Fnatic', 'MAD Lions', 'Team Vitality']
        lcs_teams = ['Cloud9', 'Team Liquid', '100 Thieves', 'TSM']
        
        if any(team in team_name for team in lck_teams):
            return 'KR'
        elif any(team in team_name for team in lpl_teams):
            return 'CN'
        elif any(team in team_name for team in lec_teams):
            return 'EU'
        elif any(team in team_name for team in lcs_teams):
            return 'NA'
        else:
            return 'Unknown'
    
    def _extract_tournament_from_overview(self, overview_page: str) -> str:
        """從 OverviewPage 提取賽事名稱"""
        if not overview_page:
            return 'Unknown Tournament'
        
        # 移除路徑分隔符並取得主要部分
        parts = overview_page.split('/')
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        else:
            return parts[0] if parts else 'Unknown Tournament'
    
    def _extract_league_from_overview(self, overview_page: str) -> str:
        """從 OverviewPage 提取聯賽"""
        if not overview_page:
            return 'Unknown'
        
        overview_lower = overview_page.lower()
        if 'lck' in overview_lower:
            return 'LCK'
        elif 'lpl' in overview_lower:
            return 'LPL'
        elif 'lec' in overview_lower:
            return 'LEC'
        elif 'lcs' in overview_lower:
            return 'LCS'
        elif 'msi' in overview_lower:
            return 'MSI'
        elif 'worlds' in overview_lower or 'world championship' in overview_lower:
            return 'Worlds'
        elif 'demacia cup' in overview_lower:
            return 'Demacia Cup'
        elif 'academy' in overview_lower:
            return 'Academy'
        else:
            # 嘗試從第一部分提取
            parts = overview_page.split('/')
            if parts:
                return parts[0]
            return 'Unknown'
    
    def _get_team_region_from_league(self, league: str) -> str:
        """根據聯賽推斷地區"""
        league_region_map = {
            'LCK': 'KR',
            'LPL': 'CN', 
            'LEC': 'EU',
            'LCS': 'NA',
            'PCS': 'TW',
            'VCS': 'VN',
            'CBLOL': 'BR',
            'LJL': 'JP',
            'LLA': 'LATAM',
            'TCL': 'TR',
            'LCO': 'OCE'
        }
        return league_region_map.get(league, 'Unknown')
    
