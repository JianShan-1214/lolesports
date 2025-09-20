# Requirements Document

## Introduction

LOL比賽通知系統是一個MVP應用程式，讓用戶能夠訂閱特定的英雄聯盟戰隊，並在這些戰隊有比賽時透過Telegram機器人接收通知。系統使用Streamlit作為主要應用框架，並透過Leaguepedia API獲取比賽資料。

## Requirements

### Requirement 1

**User Story:** 作為一個LOL電競愛好者，我想要能夠訂閱我喜歡的戰隊，這樣我就不會錯過他們的比賽。

#### Acceptance Criteria

1. WHEN 用戶訪問Streamlit應用界面 THEN 系統 SHALL 顯示可用戰隊列表
2. WHEN 用戶選擇一個或多個戰隊進行訂閱 THEN 系統 SHALL 保存用戶的訂閱偏好
3. WHEN 用戶提供Telegram用戶ID THEN 系統 SHALL 將其與訂閱資料關聯
4. WHEN 用戶提交訂閱表單 THEN 系統 SHALL 確認訂閱成功

### Requirement 2

**User Story:** 作為系統管理員，我想要系統能夠自動從Leaguepedia獲取最新的比賽資料，這樣通知資訊才會準確及時。

#### Acceptance Criteria

1. WHEN 系統啟動時 THEN 系統 SHALL 連接到Leaguepedia API
2. WHEN 系統查詢比賽資料時 THEN 系統 SHALL 獲取未來24-48小時內的比賽安排
3. IF API請求失敗 THEN 系統 SHALL 記錄錯誤並重試
4. WHEN 獲取到新的比賽資料時 THEN 系統 SHALL 更新本地比賽資料庫

### Requirement 3

**User Story:** 作為訂閱用戶，我想要在我關注的戰隊有比賽時收到Telegram通知，這樣我就能及時觀看比賽。

#### Acceptance Criteria

1. WHEN 系統檢測到訂閱戰隊有即將開始的比賽時 THEN 系統 SHALL 準備通知訊息
2. WHEN 發送通知時 THEN Telegram機器人 SHALL 向訂閱用戶發送包含比賽詳情的訊息
3. WHEN 比賽開始前1小時 THEN 系統 SHALL 發送提醒通知
4. IF Telegram訊息發送失敗 THEN 系統 SHALL 記錄錯誤並重試最多3次

### Requirement 4

**User Story:** 作為用戶，我想要能夠管理我的訂閱，這樣我可以新增或移除戰隊訂閱。

#### Acceptance Criteria

1. WHEN 用戶訪問訂閱管理頁面 THEN 系統 SHALL 顯示當前訂閱的戰隊列表
2. WHEN 用戶選擇取消訂閱某個戰隊 THEN 系統 SHALL 移除該訂閱
3. WHEN 用戶新增新的戰隊訂閱 THEN 系統 SHALL 更新訂閱列表
4. WHEN 用戶更新訂閱設定 THEN 系統 SHALL 確認變更成功

### Requirement 5

**User Story:** 作為開發者，我想要系統有基本的錯誤處理和日誌記錄，這樣我可以監控系統運行狀況和排除問題。

#### Acceptance Criteria

1. WHEN 系統發生錯誤時 THEN 系統 SHALL 記錄詳細的錯誤日誌
2. WHEN API調用失敗時 THEN 系統 SHALL 實施重試機制
3. WHEN 系統運行時 THEN 系統 SHALL 記錄關鍵操作的日誌
4. IF 系統遇到致命錯誤 THEN 系統 SHALL 優雅地處理並提供有意義的錯誤訊息