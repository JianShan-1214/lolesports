# 技術堆疊

## 重要規範
- **套件管理**: 必須使用 uv 進行所有 Python 套件管理和執行，禁止使用 pip、conda 或其他工具
- **溝通語言**: 所有溝通、註解、文件和變數命名都必須使用繁體中文

## 核心框架
- **Streamlit**: 主要的網頁應用程式框架，用於 UI 和後端邏輯
- **Python 3.11+**: 主要程式語言
- **uv**: 唯一指定的 Python 套件管理工具

## 資料儲存
- **SQLite**: 輕量級本地資料庫，用於使用者訂閱和比賽資料
- **JSON 檔案**: 配置的替代輕量級儲存選項

## 外部 API
- **Leaguepedia API**: 英雄聯盟比賽資料和戰隊資訊來源
- **Telegram Bot API**: 用於向使用者發送通知

## 主要函式庫
- **APScheduler**: 背景任務排程，用於定期資料獲取和通知
- **requests** 或 **httpx**: HTTP 客戶端，用於 API 通訊
- **sqlite3**: 資料庫操作
- **logging**: 系統日誌記錄和錯誤追蹤
- **pytest**: 測試框架
- **dataclasses**: 資料模型定義

## 套件管理規範
**重要**: 本專案嚴格要求使用 uv 進行所有 Python 相關操作，絕對不可使用 pip、conda、pipenv 或其他套件管理工具。

### 專案初始化
```bash
# 初始化新專案
uv init

# 設定 Python 版本
uv python pin 3.11
```

### 套件管理
```bash
# 新增套件
uv add streamlit apscheduler requests pytest

# 新增開發用套件
uv add --dev pytest-cov black flake8

# 移除套件
uv remove package-name

# 同步套件（安裝所有相依套件）
uv sync
```

### 執行指令
```bash
# 執行應用程式
uv run streamlit run main.py

# 執行 Python 腳本
uv run python script.py

# 執行測試
uv run pytest

# 執行測試並顯示覆蓋率
uv run pytest --cov=src tests/

# 格式化程式碼
uv run black src/

# 檢查程式碼風格
uv run flake8 src/
```

### 測試指令
```bash
# 只執行單元測試
uv run pytest tests/unit/

# 執行整合測試
uv run pytest tests/integration/

# 執行詳細輸出測試
uv run pytest -v

# 執行特定測試檔案
uv run pytest tests/unit/test_models.py
```

## 架構模式
- **單一整體式 Streamlit 應用程式**，具有模組化元件
- **服務層模式**，用於 API 整合和業務邏輯
- **儲存庫模式**，用於資料存取抽象化
- **背景任務排程**，用於自動化操作