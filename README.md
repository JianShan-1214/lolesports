# LOL比賽通知系統

一個最小可行產品 (MVP) 應用程式，讓使用者能夠訂閱特定的英雄聯盟戰隊，並在這些戰隊有比賽時透過 Telegram 接收通知。

## 功能特色

- 🎮 **戰隊訂閱管理** - 透過網頁介面訂閱喜愛的戰隊
- 📱 **Telegram通知** - 自動發送比賽提醒到您的Telegram
- 📊 **即時比賽資料** - 從Leaguepedia API獲取最新比賽資訊
- ⚙️ **訂閱管理** - 輕鬆管理和修改您的戰隊訂閱
- 📈 **系統監控** - 即時查看系統狀態和通知歷史

## 技術架構

- **前端框架**: Streamlit
- **程式語言**: Python 3.11+
- **套件管理**: uv
- **資料存儲**: SQLite
- **外部API**: Leaguepedia API, Telegram Bot API
- **背景任務**: APScheduler

## 快速開始

### 1. 環境需求

- Docker 20.10 或更高版本
- Docker Compose 2.0 或更高版本

### 2. 專案設定

```bash
# 複製專案
git clone <repository-url>
cd lol-match-notification-system

# 複製環境變數範本
cp .env.template .env
```

### 3. 配置 Telegram Bot

1. 建立 Telegram Bot:
   - 在 Telegram 中搜尋 @BotFather
   - 使用 `/newbot` 指令建立新的 Bot
   - 取得 Bot Token

2. 設定環境變數:
   ```bash
   # 編輯 .env 檔案
   TELEGRAM_BOT_TOKEN=your_actual_bot_token
   ```

### 4. 使用 Docker 部署

```bash
# 建置並啟動服務
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f
```

應用程式將在 `http://localhost:8501` 啟動。

## 使用說明

### 訂閱戰隊

1. 開啟應用程式並前往「戰隊訂閱」頁面
2. 輸入您的Telegram使用者ID（可透過@userinfobot取得）
3. 選擇想要訂閱的戰隊
4. 點擊「儲存訂閱」

### 管理訂閱

1. 前往「訂閱管理」頁面
2. 輸入您的Telegram使用者ID
3. 新增或移除戰隊訂閱
4. 發送測試通知確認設定正確

### 監控系統

1. 前往「系統狀態」頁面
2. 查看系統健康狀況
3. 監控背景任務執行狀態
4. 檢視通知歷史記錄

## 管理和維護

### 容器管理

```bash
# 停止服務
docker-compose down

# 重新啟動服務
docker-compose restart

# 查看容器狀態
docker-compose ps

# 查看即時日誌
docker-compose logs -f lol-notification-system
```

### 資料備份

```bash
# 備份資料庫
docker-compose exec lol-notification-system cp /app/data/subscriptions.db /app/data/backup_$(date +%Y%m%d).db

# 備份到本地
docker cp lol-notification-system:/app/data/subscriptions.db ./backup_$(date +%Y%m%d).db
```

### 系統升級

```bash
# 停止服務
docker-compose down

# 更新程式碼
git pull origin main

# 重新建置並啟動
docker-compose build --no-cache
docker-compose up -d
```

## 故障排除

### 常見問題

1. **Telegram通知無法發送**
   - 檢查Bot Token是否正確設定
   - 確認使用者ID格式正確
   - 檢查網路連接

2. **無法取得比賽資料**
   - 檢查Leaguepedia API連接狀態
   - 確認網路連接正常
   - 查看系統日誌了解詳細錯誤

3. **背景任務未執行**
   - 檢查系統狀態頁面的任務狀態
   - 重新啟動背景任務
   - 查看日誌檔案

### 日誌檔案

系統日誌存放在 `logs/app.log`，包含詳細的錯誤資訊和系統運行狀態。

## 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案。

## 聯絡資訊

如有問題或建議，請透過以下方式聯絡：

- 建立 Issue
- 發送 Pull Request
- 聯絡專案維護者

---

**注意**: 這是一個MVP版本，功能可能會持續更新和改進。