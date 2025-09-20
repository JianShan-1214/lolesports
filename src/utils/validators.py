"""
資料驗證工具模組
提供各種資料驗證功能
"""

import re
from typing import Optional, List

def validate_telegram_user_id(user_id: str) -> tuple[bool, Optional[str]]:
    """
    驗證Telegram使用者ID格式
    
    Args:
        user_id: 要驗證的使用者ID
        
    Returns:
        tuple: (是否有效, 錯誤訊息)
    """
    if not user_id:
        return False, "使用者ID不能為空"
    
    # 移除空白字元
    user_id = user_id.strip()
    
    # 檢查是否為純數字
    if not user_id.isdigit():
        return False, "使用者ID必須為數字"
    
    # 檢查長度（Telegram使用者ID通常為5-10位數字）
    if len(user_id) < 5 or len(user_id) > 15:
        return False, "使用者ID長度應為5-15位數字"
    
    return True, None

def validate_team_name(team_name: str) -> tuple[bool, Optional[str]]:
    """
    驗證戰隊名稱格式
    
    Args:
        team_name: 要驗證的戰隊名稱
        
    Returns:
        tuple: (是否有效, 錯誤訊息)
    """
    if not team_name:
        return False, "戰隊名稱不能為空"
    
    # 移除前後空白字元
    team_name = team_name.strip()
    
    # 檢查長度
    if len(team_name) < 1 or len(team_name) > 50:
        return False, "戰隊名稱長度應為1-50個字元"
    
    # 檢查是否包含危險字元（只排除控制字元和一些特殊符號）
    # 支援幾乎所有國際字元
    if re.search(r'[\x00-\x1f\x7f-\x9f<>"\'\\\|]', team_name):
        return False, "戰隊名稱包含不安全的字元"
    
    return True, None

def validate_telegram_username(username: str) -> tuple[bool, Optional[str]]:
    """
    驗證Telegram使用者名稱格式
    
    Args:
        username: 要驗證的使用者名稱
        
    Returns:
        tuple: (是否有效, 錯誤訊息)
    """
    if not username:
        return True, None  # 使用者名稱是選填的
    
    # 移除前後空白字元和@符號
    username = username.strip().lstrip('@')
    
    # 檢查長度
    if len(username) < 5 or len(username) > 32:
        return False, "使用者名稱長度應為5-32個字元"
    
    # 檢查格式（只能包含字母、數字和底線，且必須以字母開頭）
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return False, "使用者名稱必須以字母開頭，只能包含字母、數字和底線"
    
    return True, None

def validate_match_id(match_id: str) -> tuple[bool, Optional[str]]:
    """
    驗證比賽ID格式
    
    Args:
        match_id: 要驗證的比賽ID
        
    Returns:
        tuple: (是否有效, 錯誤訊息)
    """
    if not match_id:
        return False, "比賽ID不能為空"
    
    # 移除前後空白字元
    match_id = match_id.strip()
    
    # 檢查長度
    if len(match_id) < 1 or len(match_id) > 100:
        return False, "比賽ID長度應為1-100個字元"
    
    return True, None

def validate_notification_message(message: str) -> tuple[bool, Optional[str]]:
    """
    驗證通知訊息格式
    
    Args:
        message: 要驗證的通知訊息
        
    Returns:
        tuple: (是否有效, 錯誤訊息)
    """
    if not message:
        return False, "通知訊息不能為空"
    
    # 移除前後空白字元
    message = message.strip()
    
    # 檢查長度（Telegram訊息最大長度為4096字元）
    if len(message) > 4096:
        return False, "通知訊息長度不能超過4096個字元"
    
    return True, None

def sanitize_input(input_str: str) -> str:
    """
    清理輸入字串，移除危險字元
    
    Args:
        input_str: 要清理的字串
        
    Returns:
        str: 清理後的字串
    """
    if not input_str:
        return ""
    
    # 移除前後空白字元
    cleaned = input_str.strip()
    
    # 移除控制字元
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
    
    return cleaned

def validate_subscription_data(user_id: str, username: str, teams: List[str]) -> tuple[bool, Optional[str]]:
    """
    驗證訂閱資料的完整性
    
    Args:
        user_id: 使用者ID
        username: 使用者名稱
        teams: 戰隊列表
        
    Returns:
        tuple: (是否有效, 錯誤訊息)
    """
    # 驗證使用者ID
    is_valid, error_msg = validate_telegram_user_id(user_id)
    if not is_valid:
        return False, f"使用者ID錯誤: {error_msg}"
    
    # 驗證使用者名稱
    is_valid, error_msg = validate_telegram_username(username)
    if not is_valid:
        return False, f"使用者名稱錯誤: {error_msg}"
    
    # 驗證戰隊列表
    if not teams:
        return False, "至少需要訂閱一個戰隊"
    
    if len(teams) > 20:
        return False, "最多只能訂閱20個戰隊"
    
    # 驗證每個戰隊名稱
    for team in teams:
        is_valid, error_msg = validate_team_name(team)
        if not is_valid:
            return False, f"戰隊名稱 '{team}' 錯誤: {error_msg}"
    
    return True, None