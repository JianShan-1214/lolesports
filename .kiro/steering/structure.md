# 專案結構

## 目錄組織

```
├── main.py                 # Streamlit 應用程式進入點
├── pyproject.toml         # uv 專案配置和相依套件
├── config/
│   ├── settings.py        # 配置管理
│   └── config.json        # 預設配置檔案
├── src/
│   ├── models/            # 資料模型和架構
│   │   ├── __init__.py
│   │   ├── user.py        # 使用者訂閱模型
│   │   ├── team.py        # 戰隊模型
│   │   ├── match.py       # 比賽模型
│   │   └── notification.py # 通知記錄模型
│   ├── services/          # 業務邏輯和外部整合
│   │   ├── __init__.py
│   │   ├── data_manager.py    # 本地資料儲存操作
│   │   ├── leaguepedia_api.py # Leaguepedia API 客戶端
│   │   ├── telegram_api.py    # Telegram Bot API 客戶端
│   │   ├── notification_manager.py # 通知邏輯
│   │   └── scheduler_manager.py    # 背景任務排程
│   ├── ui/                # Streamlit UI 元件
│   │   ├── __init__.py
│   │   ├── subscription_page.py   # 戰隊訂閱介面
│   │   ├── management_page.py     # 訂閱管理
│   │   └── status_page.py         # 系統狀態和日誌
│   └── utils/             # 工具函數
│       ├── __init__.py
│       ├── logging_config.py  # 日誌設定
│       └── validators.py      # 資料驗證輔助工具
├── tests/
│   ├── unit/              # 單元測試
│   │   ├── test_models.py
│   │   ├── test_services.py
│   │   └── test_utils.py
│   ├── integration/       # 整合測試
│   │   ├── test_api_integration.py
│   │   └── test_end_to_end.py
│   └── fixtures/          # 測試資料和模擬物件
├── data/                  # 本地資料儲存
│   ├── subscriptions.db   # SQLite 資料庫
│   └── cache/            # 暫存檔案
└── logs/                 # 應用程式日誌
    └── app.log
```

## 檔案命名慣例
- Python 檔案和目錄使用 **snake_case**
- 使用**描述性名稱**，清楚表明模組的用途
- 測試檔案以 `test_` 為前綴
- 使用 `__init__.py` 檔案讓目錄成為 Python 套件

## 模組組織
- **models/**: 純資料類別與驗證邏輯
- **services/**: 業務邏輯、API 客戶端和核心功能
- **ui/**: Streamlit 頁面元件和 UI 邏輯
- **utils/**: 共用工具函數和輔助工具
- **config/**: 配置管理和設定

## 匯入慣例
- 在同一套件內使用相對匯入
- 跨套件匯入使用 `src.` 開頭
- 分組匯入：標準函式庫、第三方套件、本地匯入