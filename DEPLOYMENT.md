# LOL 比賽通知系統部署指南

## 系統需求

### 最低系統需求
- Docker 20.10 或更高版本
- Docker Compose 2.0 或更高版本
- 2GB RAM
- 1GB 可用磁碟空間
- 網路連線（用於 API 存取）

### 建議系統需求
- Docker 24.0+
- Docker Compose 2.20+
- 4GB RAM
- 5GB 可用磁碟空間
- 穩定的網路連線

## Docker 部署

### 快速開始

#### 1. 準備專案
```bash
# 複製專案
git clone <repository-url>
cd lol-match-notification-system

# 複製環境變數範本
cp .env.template .env
```

#### 2. 配置 Telegram Bot
編輯 `.env` 檔案，填入您的 Telegram Bot Token：
```bash
# 必填：Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_actual_bot_token

# 其他配置保持預設值即可
```

#### 3. 使用 Docker Compose 部署（推薦）
```bash
# 建置並啟動服務
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看即時日誌
docker-compose logs -f

# 停止服務
docker-compose down
```

#### 4. 使用 Docker 指令部署
```bash
# 建置映像檔
docker build -t lol-notification-system .

# 執行容器
docker run -d \
  --name lol-notification-system \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  --restart unless-stopped \
  lol-notification-system
```

### 存取應用程式
部署完成後，開啟瀏覽器存取：`http://localhost:8501`

## 配置說明

### 環境變數配置

| 變數名稱 | 必填 | 預設值 | 說明 |
|---------|------|--------|------|
| `TELEGRAM_BOT_TOKEN` | 是 | - | Telegram Bot 的 API Token |
| `DATABASE_PATH` | 否 | `data/subscriptions.db` | SQLite 資料庫檔案路徑 |
| `LOGGING_LEVEL` | 否 | `INFO` | 日誌等級 (DEBUG/INFO/WARNING/ERROR) |
| `LOGGING_FILE_PATH` | 否 | `logs/app.log` | 日誌檔案路徑 |
| `SCHEDULER_MATCH_DATA_FETCH_INTERVAL` | 否 | `30` | 比賽資料獲取間隔（分鐘） |
| `SCHEDULER_NOTIFICATION_CHECK_INTERVAL` | 否 | `5` | 通知檢查間隔（分鐘） |

### Telegram Bot 設定

1. 在 Telegram 中搜尋 @BotFather
2. 發送 `/newbot` 指令建立新的 Bot
3. 按照指示設定 Bot 名稱和用戶名
4. 取得 Bot Token（格式類似：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）
5. 將 Token 填入 `.env` 檔案的 `TELEGRAM_BOT_TOKEN`

## 監控和維護

### 日誌檢查
```bash
# 查看容器日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs -f lol-notification-system

# 查看本地日誌檔案
tail -f logs/app.log
```

### 健康檢查
- 應用程式提供健康檢查端點：`http://localhost:8501/_stcore/health`
- 系統狀態頁面：`http://localhost:8501` → 系統狀態頁面

### 資料備份
```bash
# 備份資料庫
cp data/subscriptions.db data/subscriptions_backup_$(date +%Y%m%d).db

# 備份日誌
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

## 故障排除

### 常見問題

#### 1. 容器無法啟動
- 檢查 Docker 服務：`docker --version` 和 `docker-compose --version`
- 檢查環境變數：確認 `.env` 檔案存在且配置正確
- 查看容器日誌：`docker-compose logs lol-notification-system`

#### 2. Telegram 通知無法發送
- 驗證 Bot Token 是否正確
- 檢查網路連線
- 查看錯誤日誌：`tail -f logs/error.log`

#### 3. 比賽資料無法獲取
- 檢查網路連線到 Leaguepedia
- 查看 API 調用日誌
- 確認 API 端點是否正常

#### 4. Docker 容器問題
```bash
# 檢查容器狀態
docker-compose ps

# 查看容器日誌
docker-compose logs lol-notification-system

# 重新建置容器
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 效能調優

#### 記憶體使用優化
- 調整 `SCHEDULER_MATCH_DATA_FETCH_INTERVAL` 減少 API 調用頻率
- 定期清理舊日誌檔案

#### 網路優化
- 設定適當的 API 超時時間
- 使用連線池減少連線開銷

## 安全考量

### 基本安全措施
1. **環境變數保護**：確保 `.env` 檔案不被提交到版本控制
2. **網路安全**：使用防火牆限制不必要的埠號存取
3. **定期更新**：保持依賴套件為最新版本
4. **日誌監控**：定期檢查錯誤日誌，注意異常活動

### 生產環境建議
1. 使用反向代理（如 nginx）
2. 設定 HTTPS 憑證
3. 實施速率限制
4. 定期備份資料

## 升級指南

### 應用程式升級
```bash
# 停止服務
docker-compose down

# 更新程式碼
git pull origin main

# 重新建置並啟動
docker-compose build --no-cache
docker-compose up -d

# 驗證升級
docker-compose ps
docker-compose logs -f
```

### 資料庫遷移
目前使用 SQLite，升級時通常不需要特殊的遷移步驟。如有需要，會在版本說明中提供具體指示。