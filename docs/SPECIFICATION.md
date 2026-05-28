# Dispatch Service Specification (Ollama 本地版)

## 1. 概述

本服務使用 **Ollama** 本地大語言模型進行志工派發。與雲端 API 相比，本地部署提供：
- 完整隱私性（數據不離開本地）
- 穩定性（不依賴網路連線）
- 成本控制（一次性下載模型）

## 2. 架構

- **DispatchService 類**：主要邏輯，負責編排 AI 調用和本地演算法
- **Ollama API 客戶端**：HTTP 請求直接呼叫本地 Ollama 服務
- **本地演算法**：技能匹配 + 距離優先，保證總是能給出分配

## 3. 環境配置

**本地 Ollama：**
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_DISPATCH=mistral
OLLAMA_MODEL_DEBUG=neural-chat
```

**遠端 Ollama (Tailscale VPN)：**
```env
OLLAMA_BASE_URL=http://100.76.39.84:11434
OLLAMA_MODEL_DISPATCH=mistral
OLLAMA_MODEL_DEBUG=neural-chat
```
OLLAMA_MODEL_DEBUG=neural-chat
```

## 4. API 合約

### 輸入：DispatchRequest
```json
{
  "metadata": {"incident_id": "xxx", "priority_weighting": "balanced"},
  "volunteers": [
    {"id": "vol_01", "skills": ["medical"], "location": {"lat": 23.0, "lng": 121.5}, "availability": true}
  ],
  "tasks": [
    {"id": "task_101", "type_id": "medical", "location": {"lat": 23.1, "lng": 121.5}, "urgency": 5}
  ],
  "work_types": []
}
```

### 輸出：Response
```json
{
  "status": "success",
  "dispatch_id": "uuid-xxx",
  "assignments": [
    {
      "task_id": "task_101",
      "assigned_volunteers": ["vol_01"],
      "eta_minutes": 15,
      "reasoning_summary": "[Ollama 派發模型] 指派 vol_01"
    }
  ]
}
```

## 5. 工作流程

```
1. 接收 DispatchRequest
   ↓
2. 過濾可用志工 (availability=true)
   ↓
3. 按緊急度排序任務
   ↓
4. 對每個任務：
   ├─ 嘗試用派發模型 (mistral) 給出建議
   ├─ 若無效，用偵錯模型 (neural-chat) 驗證
   ├─ 若仍無效，用本地演算法分配
   └─ 將該志工從可用清單移除
   ↓
5. 回傳所有分配
```

## 6. 本地演算法

**目的**：若 Ollama 不可用，確保系統仍能進行分配

**步驟**：
1. 對每個志工，檢查其 `skills` 是否包含任務的 `type_id`
2. 優先選擇有技能匹配的志工
3. 若無匹配志工，則考慮全部可用志工
4. 在候選者中選擇距離最近的（使用 Haversine 公式）
5. 計算 ETA = (距離 / 40 km/h) × 60 + 5 分鐘

**範例**：
- Task: medical, 3 位志工，距離分別 1km, 0.5km, 2km
- 有技能匹配的：vol_01(1km), vol_02(2km)
- 選擇最近的：vol_01
- ETA = (1/40)*60 + 5 = 6.5 分鐘

## 7. 失敗模式與處理

| 情況 | 行為 |
|------|------|
| Ollama 無法連線 | 直接用本地演算法 |
| 派發模型超時 | 異常捕捉，進入偵錯/降級 |
| 派發模型回傳無效 ID | 呼叫偵錯模型二次驗證 |
| 偵錯模型也失敗 | 用本地演算法 |
| JSON 解析失敗 | 用本地演算法 |

## 8. 日誌等級

| 等級 | 用途 |
|------|------|
| INFO | 模型呼叫、任務開始 |
| WARNING | 模型回傳異常、需降級 |
| ERROR | 異常捕捉、連線失敗 |

## 9. 模型選擇建議

### 派發模型（OLLAMA_MODEL_DISPATCH）
- **mistral** (推薦)：7B，快速，足夠聰慧
- llama2：7B，通用
- orca-mini：3B，最輕量

### 偵錯模型（OLLAMA_MODEL_DEBUG）
- **neural-chat** (推薦)：8B，對話優化，驗證準確
- dolphin：7B，多功能
- openchat：7B，平衡型

## 10. 性能考量

- **首次啟動**：模型載入需要 30 秒 ~ 5 分鐘（取決於模型大小和 GPU）
- **推理時間**：per task 約 2-5 秒（GPU）或 10-30 秒（CPU）
- **記憶體**：mistral 約 4GB，neural-chat 約 5GB

## 11. 測試計畫

1. **單元測試**：本地演算法邏輯
2. **集成測試**：
   - Ollama 正常：驗證 AI 輸出
   - Ollama 中斷：驗證降級
   - 邊界情況：無志工、無任務

## 12. 延伸建議

- 添加模型量化支持（Q4 版本更輕量）
- 實現批量處理以提升吞吐量
- 添加決策日誌詳細版本用於審計
- 支援多模型 ensemble 提高準確性

