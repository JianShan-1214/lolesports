# LOL 比賽通知系統 API 參考文件

## 概述

本文件描述 LOL 比賽通知系統的內部 API 架構和外部 API 整合。系統主要透過 Streamlit 提供網頁介面，並整合多個外部 API 服務。

## 系統架構

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   Business Logic │    │  External APIs  │
│                 │    │                  │    │                 │
│ - 戰隊訂閱      │◄──►│ - 訂閱管理       │◄──►│ - Leaguepedia   │
│ - 訂閱管理      │    │ - 通知服務       │    │ - Telegram Bot  │
│ - 系統狀態      │    │ - 資料管理       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Local Storage  │
                       │                  │
                       │ - SQLite DB      │
                       │ - 日誌檔案       │
                       └──────────────────┘
```

## 核心服務 API

### 1. 資料管理服務 (DataManager)

#### 類別：`src.services.data_manager.DataManager`

##### 方法

**`add_subscription(user_id: str, team_name: str) -> bool`**
- **描述**：新增使用者戰隊訂閱
- **參數**：
  - `user_id`: Telegram 使用者 ID（字串格式）
  - `team_name`: 戰隊名稱
- **回傳值**：成功返回 `True`，失敗返回 `False`
- **例外**：`DatabaseError` 當資料庫操作失敗時

**`remove_subscription(user_id: str, team_name: str) -> bool`**
- **描述**：移除使用者戰隊訂閱
- **參數**：
  - `user_id`: Telegram 使用者 ID
  - `team_name`: 戰隊名稱
- **回傳值**：成功返回 `True`，失敗返回 `False`

**`get_user_subscriptions(user_id: str) -> List[str]`**
- **描述**：取得使用者的所有訂閱戰隊
- **參數**：
  - `user_id`: Telegram 使用者 ID
- **回傳值**：戰隊名稱列表

**`get_team_subscribers(team_name: str) -> List[str]`**
- **描述**：取得訂閱特定戰隊的所有使用者
- **參數**：
  - `team_name`: 戰隊名稱
- **回傳值**：使用者 ID 列表

### 2. Leaguepedia API 服務

#### 類別：`src.services.leaguepedia_api.LeaguepediaAPI`

##### 方法

**`get_upcoming_matches(hours_ahead: int = 24) -> List[Dict]`**
- **描述**：取得未來指定時間內的比賽資料
- **參數**：
  - `hours_ahead`: 查詢未來幾小時內的比賽（預設 24 小時）
- **回傳值**：比賽資料字典列表
- **回傳格式**：
```python
[
    {
        "match_id": "string",
        "team1": "string",
        "team2": "string",
        "start_time": "datetime",
        "tournament": "string",
        "status": "string"
    }
]
```

**`get_team_matches(team_name: str, days_ahead: int = 7) -> List[Dict]`**
- **描述**：取得特定戰隊的未來比賽
- **參數**：
  - `team_name`: 戰隊名稱
  - `days_ahead`: 查詢未來幾天內的比賽
- **回傳值**：比賽資料字典列表

### 3. Telegram API 服務

#### 類別：`src.services.telegram_api.TelegramAPI`

##### 方法

**`send_message(user_id: str, message: str) -> bool`**
- **描述**：發送訊息給指定使用者
- **參數**：
  - `user_id`: Telegram 使用者 ID
  - `message`: 要發送的訊息內容
- **回傳值**：成功返回 `True`，失敗返回 `False`

**`send_match_notification(user_id: str, match_data: Dict) -> bool`**
- **描述**：發送比賽通知
- **參數**：
  - `user_id`: Telegram 使用者 ID
  - `match_data`: 比賽資料字典
- **回傳值**：成功返回 `True`，失敗返回 `False`

### 4. 通知管理服務

#### 類別：`src.services.notification_manager.NotificationManager`

##### 方法

**`check_and_send_notifications() -> int`**
- **描述**：檢查並發送所有待發送的通知
- **回傳值**：發送的通知數量

**`schedule_match_notification(match_data: Dict, subscribers: List[str]) -> None`**
- **描述**：排程比賽通知
- **參數**：
  - `match_data`: 比賽資料
  - `subscribers`: 訂閱者列表

## 資料模型

### 使用者訂閱 (UserSubscription)

```python
@dataclass
class UserSubscription:
    user_id: str          # Telegram 使用者 ID
    team_name: str        # 戰隊名稱
    created_at: datetime  # 訂閱建立時間
    is_active: bool       # 訂閱是否啟用
```

### 比賽資料 (Match)

```python
@dataclass
class Match:
    match_id: str         # 比賽唯一識別碼
    team1: str           # 戰隊1名稱
    team2: str           # 戰隊2名稱
    start_time: datetime # 比賽開始時間
    tournament: str      # 賽事名稱
    status: str          # 比賽狀態
    created_at: datetime # 資料建立時間
```

### 通知記錄 (NotificationLog)

```python
@dataclass
class NotificationLog:
    log_id: str          # 日誌唯一識別碼
    user_id: str         # 接收者 ID
    match_id: str        # 相關比賽 ID
    message: str         # 通知內容
    sent_at: datetime    # 發送時間
    status: str          # 發送狀態 (success/failed)
    error_message: str   # 錯誤訊息（如果有）
```

## 外部 API 整合

### Leaguepedia API

#### 基本資訊
- **基礎 URL**：`https://lol.fandom.com/api.php`
- **認證**：無需認證
- **速率限制**：建議每秒不超過 10 次請求

#### 主要端點

**取得比賽資料**
```
GET /api.php?action=cargoquery&tables=MatchSchedule&fields=...
```

**查詢參數**：
- `action=cargoquery`：使用 Cargo 查詢
- `tables=MatchSchedule`：查詢比賽排程表
- `fields`：指定要取得的欄位
- `where`：查詢條件
- `order_by`：排序方式

#### 回應格式
```json
{
    "cargoquery": [
        {
            "title": {
                "Team1": "T1",
                "Team2": "Gen.G",
                "DateTime UTC": "2024-03-15 09:00:00",
                "Tournament": "LCK Spring 2024"
            }
        }
    ]
}
```

### Telegram Bot API

#### 基本資訊
- **基礎 URL**：`https://api.telegram.org/bot{token}`
- **認證**：Bot Token（在 URL 中）
- **速率限制**：每秒最多 30 則訊息

#### 主要端點

**發送訊息**
```
POST /bot{token}/sendMessage
```

**請求體**：
```json
{
    "chat_id": "user_id",
    "text": "message_content",
    "parse_mode": "Markdown"
}
```

**回應格式**：
```json
{
    "ok": true,
    "result": {
        "message_id": 123,
        "date": 1647331200,
        "text": "message_content"
    }
}
```

## 錯誤處理

### 錯誤類型

**`DatabaseError`**
- **描述**：資料庫操作相關錯誤
- **常見原因**：連線失敗、SQL 語法錯誤、資料約束違反

**`APIError`**
- **描述**：外部 API 調用錯誤
- **常見原因**：網路連線問題、API 限制、認證失敗

**`NotificationError`**
- **描述**：通知發送相關錯誤
- **常見原因**：Telegram API 錯誤、使用者封鎖 Bot

### 錯誤回應格式

```python
{
    "error": True,
    "error_type": "DatabaseError",
    "message": "無法連接到資料庫",
    "details": "Connection timeout after 30 seconds",
    "timestamp": "2024-03-15T10:30:00Z"
}
```

## 配置參數

### 環境變數

| 變數名稱 | 類型 | 預設值 | 描述 |
|---------|------|--------|------|
| `TELEGRAM_BOT_TOKEN` | string | - | Telegram Bot API Token |
| `DATABASE_PATH` | string | `data/subscriptions.db` | SQLite 資料庫路徑 |
| `LEAGUEPEDIA_TIMEOUT` | int | 30 | API 請求超時時間（秒） |
| `TELEGRAM_TIMEOUT` | int | 30 | Telegram API 超時時間（秒） |
| `SCHEDULER_MATCH_DATA_FETCH_INTERVAL` | int | 30 | 資料獲取間隔（分鐘） |
| `SCHEDULER_NOTIFICATION_CHECK_INTERVAL` | int | 5 | 通知檢查間隔（分鐘） |

### 系統限制

- **最大訂閱數**：每個使用者最多 50 個戰隊
- **通知頻率**：每個使用者每小時最多 20 則通知
- **資料保留**：通知記錄保留 30 天
- **API 調用**：Leaguepedia API 每分鐘最多 60 次請求

## 開發指南

### 新增 API 端點

1. 在對應的服務類別中新增方法
2. 實作錯誤處理和日誌記錄
3. 新增單元測試
4. 更新此文件

### 測試 API

```python
# 測試資料管理 API
from src.services.data_manager import DataManager

dm = DataManager()
result = dm.add_subscription("123456789", "T1")
print(f"訂閱結果: {result}")

# 測試 Telegram API
from src.services.telegram_api import TelegramAPI

telegram = TelegramAPI()
success = telegram.send_message("123456789", "測試訊息")
print(f"發送結果: {success}")
```

### 日誌記錄

所有 API 調用都會記錄在 `logs/app.log` 中，包含：
- 請求時間
- 方法名稱
- 參數（敏感資訊會被遮罩）
- 執行時間
- 結果狀態

## 版本資訊

- **當前版本**：v0.1.0
- **API 版本**：v1
- **最後更新**：2024-03-15

## 聯絡資訊

如有 API 相關問題，請：
1. 查看日誌檔案
2. 檢查系統狀態頁面
3. 聯絡開發團隊並提供詳細錯誤資訊