# 故障排除指南

## 目錄
1. [診斷工具](#診斷工具)
2. [常見問題分類](#常見問題分類)
3. [系統啟動問題](#系統啟動問題)
4. [通知功能問題](#通知功能問題)
5. [資料同步問題](#資料同步問題)
6. [效能問題](#效能問題)
7. [網路連線問題](#網路連線問題)
8. [日誌分析](#日誌分析)
9. [緊急恢復程序](#緊急恢復程序)

## 診斷工具

### 基本檢查指令

```bash
# 檢查容器狀態
docker-compose ps

# 查看容器日誌
docker-compose logs -f

# 檢查容器資源使用
docker stats

# 檢查系統資源
df -h  # 磁碟空間
free -h  # 記憶體使用
```

### 系統健康檢查

```bash
# 檢查應用程式健康狀態
curl -f http://localhost:8501/_stcore/health

# 檢查容器內部狀態
docker-compose exec lol-notification-system ps aux

# 檢查網路連線
docker-compose exec lol-notification-system ping -c 3 lol.fandom.com
docker-compose exec lol-notification-system ping -c 3 api.telegram.org
```

## 常見問題分類

### 🔴 嚴重問題（系統無法使用）
- 容器無法啟動
- 網頁完全無法存取
- 資料庫損壞
- 記憶體不足導致系統崩潰

### 🟡 中等問題（功能受限）
- 通知發送失敗
- 資料同步延遲
- 部分功能無回應
- 效能明顯下降

### 🟢 輕微問題（使用體驗影響）
- UI 顯示異常
- 日誌警告訊息
- 偶發性錯誤
- 輕微效能問題

## 系統啟動問題

### 問題：容器無法啟動

#### 症狀
```bash
$ docker-compose up -d
ERROR: Service 'lol-notification-system' failed to build
```

#### 診斷步驟
1. **檢查 Docker 環境**
   ```bash
   docker --version
   docker-compose --version
   docker info
   ```

2. **檢查環境變數檔案**
   ```bash
   ls -la .env
   cat .env | grep -v "^#" | grep -v "^$"
   ```

3. **檢查磁碟空間**
   ```bash
   df -h
   docker system df
   ```

#### 解決方案
```bash
# 清理 Docker 資源
docker system prune -f

# 重新建置容器
docker-compose build --no-cache

# 檢查並修正 .env 檔案
cp .env.template .env
# 編輯 .env 檔案填入正確的 Token

# 重新啟動
docker-compose up -d
```

### 問題：網頁無法存取

#### 症狀
- 瀏覽器顯示「無法連線」
- 連線超時

#### 診斷步驟
1. **檢查容器狀態**
   ```bash
   docker-compose ps
   # 應該顯示 "Up" 狀態
   ```

2. **檢查埠號佔用**
   ```bash
   netstat -tlnp | grep 8501
   # 或
   lsof -i :8501
   ```

3. **檢查容器日誌**
   ```bash
   docker-compose logs lol-notification-system
   ```

#### 解決方案
```bash
# 如果埠號被佔用，修改 docker-compose.yml
# 將 "8501:8501" 改為 "8502:8501"

# 重新啟動服務
docker-compose down
docker-compose up -d

# 檢查防火牆設定（Linux）
sudo ufw status
sudo ufw allow 8501
```

## 通知功能問題

### 問題：測試通知發送失敗

#### 症狀
- 點擊「發送測試通知」後顯示錯誤
- Telegram 沒有收到訊息

#### 診斷步驟
1. **驗證 Bot Token**
   ```bash
   # 檢查 .env 檔案中的 Token
   grep TELEGRAM_BOT_TOKEN .env
   
   # 測試 Token 有效性
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
   ```

2. **驗證使用者 ID**
   ```bash
   # 使用者 ID 應該是純數字，例如：123456789
   # 不應該包含 @ 符號或其他字元
   ```

3. **檢查網路連線**
   ```bash
   docker-compose exec lol-notification-system curl -I https://api.telegram.org
   ```

#### 解決方案
```bash
# 1. 重新取得正確的 Bot Token
# 與 @BotFather 對話，使用 /token 指令

# 2. 確認使用者 ID 格式
# 與 @userinfobot 對話取得正確的數字 ID

# 3. 重新啟動服務
docker-compose restart

# 4. 檢查系統狀態頁面的詳細錯誤訊息
```

### 問題：自動通知沒有發送

#### 症狀
- 手動測試通知正常
- 但比賽時沒有收到自動通知

#### 診斷步驟
1. **檢查背景任務狀態**
   - 前往系統狀態頁面
   - 查看「背景任務」區域
   - 確認任務正在執行

2. **檢查比賽資料**
   ```bash
   # 查看日誌中的資料獲取記錄
   docker-compose logs | grep -i "match data"
   ```

3. **檢查訂閱設定**
   - 確認戰隊名稱正確
   - 確認訂閱狀態為啟用

#### 解決方案
```bash
# 重新啟動背景任務
docker-compose restart

# 檢查並調整任務間隔（如果需要）
# 編輯 .env 檔案
SCHEDULER_MATCH_DATA_FETCH_INTERVAL=15  # 改為 15 分鐘
SCHEDULER_NOTIFICATION_CHECK_INTERVAL=3  # 改為 3 分鐘

# 重新啟動應用
docker-compose down
docker-compose up -d
```

## 資料同步問題

### 問題：比賽資料不是最新的

#### 症狀
- 系統狀態頁面顯示資料更新時間過舊
- 缺少最新的比賽資訊

#### 診斷步驟
1. **檢查 API 連線**
   ```bash
   docker-compose exec lol-notification-system curl -I "https://lol.fandom.com/api.php"
   ```

2. **查看 API 調用日誌**
   ```bash
   docker-compose logs | grep -i "leaguepedia\|api"
   ```

3. **檢查系統時間**
   ```bash
   docker-compose exec lol-notification-system date
   date
   ```

#### 解決方案
```bash
# 1. 手動觸發資料更新
# 重新啟動容器會觸發立即更新
docker-compose restart

# 2. 檢查並修正系統時間
# 如果容器時間不正確，重新建置容器
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 3. 調整資料獲取頻率
# 編輯 .env 檔案
SCHEDULER_MATCH_DATA_FETCH_INTERVAL=10  # 改為 10 分鐘
```

### 問題：資料庫錯誤

#### 症狀
- 無法載入訂閱資料
- 新增訂閱失敗
- 系統日誌顯示資料庫錯誤

#### 診斷步驟
1. **檢查資料庫檔案**
   ```bash
   ls -la data/
   docker-compose exec lol-notification-system ls -la /app/data/
   ```

2. **檢查磁碟空間**
   ```bash
   df -h
   ```

3. **測試資料庫連線**
   ```bash
   docker-compose exec lol-notification-system python -c "
   import sqlite3
   conn = sqlite3.connect('/app/data/subscriptions.db')
   print('Database connection successful')
   conn.close()
   "
   ```

#### 解決方案
```bash
# 1. 備份現有資料（如果可能）
docker cp lol-notification-system:/app/data/subscriptions.db ./backup_$(date +%Y%m%d).db

# 2. 重新初始化資料庫
docker-compose down
rm -f data/subscriptions.db  # 注意：這會刪除所有訂閱資料
docker-compose up -d

# 3. 如果有備份，嘗試恢復
# 將備份檔案複製回 data/ 目錄
```

## 效能問題

### 問題：系統回應緩慢

#### 症狀
- 網頁載入時間過長
- 操作延遲明顯

#### 診斷步驟
1. **檢查系統資源**
   ```bash
   docker stats lol-notification-system
   free -h
   top
   ```

2. **檢查日誌檔案大小**
   ```bash
   ls -lh logs/
   du -sh logs/
   ```

3. **檢查資料庫大小**
   ```bash
   ls -lh data/
   ```

#### 解決方案
```bash
# 1. 清理日誌檔案
docker-compose exec lol-notification-system find /app/logs -name "*.log" -mtime +7 -delete

# 2. 調整資源限制（編輯 docker-compose.yml）
services:
  lol-notification-system:
    # ... 其他設定
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

# 3. 重新啟動服務
docker-compose down
docker-compose up -d
```

### 問題：記憶體使用過高

#### 症狀
- 系統變慢或無回應
- Docker stats 顯示記憶體使用接近 100%

#### 診斷步驟
```bash
# 檢查記憶體使用詳情
docker exec lol-notification-system ps aux --sort=-%mem | head -10

# 檢查系統記憶體
free -h
```

#### 解決方案
```bash
# 1. 重新啟動容器釋放記憶體
docker-compose restart

# 2. 調整任務頻率減少記憶體使用
# 編輯 .env 檔案
SCHEDULER_MATCH_DATA_FETCH_INTERVAL=60  # 增加到 60 分鐘
SCHEDULER_NOTIFICATION_CHECK_INTERVAL=10  # 增加到 10 分鐘

# 3. 如果問題持續，考慮增加系統記憶體
```

## 網路連線問題

### 問題：無法連接外部 API

#### 症狀
- 無法獲取比賽資料
- Telegram 通知發送失敗
- 系統日誌顯示連線超時

#### 診斷步驟
```bash
# 測試網路連線
docker-compose exec lol-notification-system ping -c 3 8.8.8.8
docker-compose exec lol-notification-system nslookup lol.fandom.com
docker-compose exec lol-notification-system curl -I https://api.telegram.org

# 檢查 DNS 設定
docker-compose exec lol-notification-system cat /etc/resolv.conf
```

#### 解決方案
```bash
# 1. 重新啟動網路服務
docker-compose down
docker-compose up -d

# 2. 修改 DNS 設定（編輯 docker-compose.yml）
services:
  lol-notification-system:
    # ... 其他設定
    dns:
      - 8.8.8.8
      - 8.8.4.4

# 3. 檢查防火牆設定
# 確保允許對外連線到 443 埠（HTTPS）
```

## 日誌分析

### 重要日誌位置
```bash
# 應用程式日誌
docker-compose logs lol-notification-system

# 本地日誌檔案
tail -f logs/app.log

# 系統日誌（Linux）
journalctl -u docker
```

### 常見錯誤訊息

#### "Connection timeout"
```bash
# 原因：網路連線問題
# 解決：檢查網路設定，重新啟動服務
```

#### "Database is locked"
```bash
# 原因：資料庫被其他程序佔用
# 解決：重新啟動容器
docker-compose restart
```

#### "Invalid bot token"
```bash
# 原因：Telegram Bot Token 不正確
# 解決：檢查並更新 .env 檔案中的 Token
```

#### "Permission denied"
```bash
# 原因：檔案權限問題
# 解決：檢查 data/ 和 logs/ 目錄權限
chmod 755 data logs
```

### 日誌等級說明
- **DEBUG**：詳細的除錯資訊
- **INFO**：一般操作資訊
- **WARNING**：警告訊息，不影響功能
- **ERROR**：錯誤訊息，可能影響功能
- **CRITICAL**：嚴重錯誤，系統可能無法正常運作

## 緊急恢復程序

### 完全重新部署
```bash
# 1. 備份重要資料
docker cp lol-notification-system:/app/data/subscriptions.db ./emergency_backup.db

# 2. 完全清理
docker-compose down -v
docker system prune -f

# 3. 重新部署
git pull origin main
docker-compose build --no-cache
docker-compose up -d

# 4. 恢復資料（如果需要）
docker cp ./emergency_backup.db lol-notification-system:/app/data/subscriptions.db
docker-compose restart
```

### 資料恢復
```bash
# 如果有資料庫備份
docker-compose down
cp backup_YYYYMMDD.db data/subscriptions.db
docker-compose up -d
```

### 緊急聯絡清單
1. **系統管理員**：檢查基礎設施
2. **網路管理員**：檢查網路連線
3. **開發團隊**：檢查應用程式問題

## 預防措施

### 定期維護
```bash
# 每週執行
docker system prune -f
docker-compose logs --tail=100 > weekly_logs_$(date +%Y%m%d).txt

# 每月執行
docker cp lol-notification-system:/app/data/subscriptions.db ./monthly_backup_$(date +%Y%m%d).db
```

### 監控設定
- 設定磁碟空間警報（< 1GB）
- 設定記憶體使用警報（> 80%）
- 監控容器健康狀態
- 定期檢查日誌錯誤

---

**注意：** 如果以上方法都無法解決問題，請聯絡技術支援並提供詳細的錯誤日誌。