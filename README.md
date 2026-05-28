# 救災志工智慧分配元件 (Disaster Volunteer Dispatcher API)

[cite_start]本元件為響應數位發展部「防災積木元件創新賽：公民科技拼出韌性臺灣」之參賽作品 [cite: 1, 2][cite_start]。本專案採「積木式設計」原則，聚焦於災變管理系統中的 **分析 (Analysis)** 功能 [cite: 7, 8, 12][cite_start]，提供一組標準化、去識別化且高擴充性的 API 服務 [cite: 79, 81]。

## 1. 問題定義 (Problem)
[cite_start]在重大災害發生時（如 2025 年花蓮馬太鞍溪堰塞湖災害事件情境）[cite: 8][cite_start]，現場通報的物資、救護需求龐雜且緊急 [cite: 15]。然而，傳統人工調度志工常面臨以下痛點：
- **專長無法精準媒合**：無法在第一時間將具備醫療、搬運或行政專長的志工投放至正確任務。
- **動態調度困難**：現場情境瞬息萬變，決策者難以同時計算所有人的地理距離與任務緊急度。

## 2. 核心解法與元件型態 (Solution & Component)
[cite_start]本作品實作型態為 **API 服務型元件 (Service Component)** [cite: 116]。
[cite_start]本元件不綁定任何前端介面（如特定網頁或 APP），可獨立部署，並能自由拼接到 LINE 機器人、Google Chat 或既有的民生公共物聯網災防平台中 [cite: 10, 22, 117, 283][cite_start]。它接收標準化的 JSON 資料，透過 Haversine 公式進行地理距離預處理 [cite: 90][cite_start]，並串接雲端大型語言模型 (Gemini API) 實現具備多步驟推理能力的 **AI Agent 智慧調度** [cite: 45, 94, 305]。

## 3. 資料交換規格 (Input / Output Specification)

[cite_start]本元件明確定義輸入與輸出格式，採用去識別化識別碼（ID），確保符合個人資料保護之資安規範 [cite: 79, 90, 207]。

# 救災志工智慧分配元件 (Disaster Volunteer Dispatcher API) - 本地 Ollama 版

本系統是一個災害應變志工調度服務，採用**本地 Ollama 模型**進行 AI 輔助分配，確保穩定性和隱私性。

## 核心特點

- ✅ **本地執行**：使用 Ollama 在本地執行 LLM，無需雲端服務
- ✅ **雙模型架構**：派發模型(快速) + 偵錯模型(驗證)
- ✅ **本地演算法保底**：若 Ollama 不可用，自動降級到確定性演算法
- ✅ **結構化日誌**：完整追蹤所有決策過程

## 環境設定

### 1. 必須安裝 Ollama
- 下載並安裝 [Ollama](https://ollama.ai)
- 啟動 Ollama 服務：`ollama serve`
- 預設 API 位址：`http://localhost:11434`

### 2. 拉取所需模型
```bash
ollama pull mistral        # 派發模型（輕量、快速）
ollama pull neural-chat    # 偵錯模型（驗證用）
```

### 3. 設定 `.env` 檔案

**本地 Ollama：**
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_DISPATCH=mistral
OLLAMA_MODEL_DEBUG=neural-chat
```

**遠端 Ollama (透過 Tailscale VPN)：**
```
# 將 100.76.39.84 替換為你 Tailscale 網路中的實際 Ollama 伺服器 IP
OLLAMA_BASE_URL=http://100.76.39.84:11434
OLLAMA_MODEL_DISPATCH=mistral
OLLAMA_MODEL_DEBUG=neural-chat
```

**Tailscale 設定步驟：**
1. 安裝並登入 Tailscale：`tailscale login`
2. 確認連線狀態：`tailscale status`
3. 在 `.env` 中填入遠端伺服器的 Tailscale IP
4. 執行 `python check_ollama.py` 驗證連線

## 快速啟動

```powershell
# 1. 安裝依賴
python -m pip install -r requirements.txt

# 2. 啟動 Ollama（另一個終端）
ollama serve

# 3. 啟動服務
uvicorn main:app --reload
```

## 工作流程

1. **接收請求**：取得任務和志工清單
2. **嘗試 AI 派發**：用 Ollama 的 mistral 模型分配
3. **驗證 AI 輸出**：若異常，用 neural-chat 模型二次驗證
4. **降級保底**：若 AI 都失敗，用本地演算法（技能匹配 + 距離優先）

## 回應格式

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

## 日誌說明

- **[Ollama 派發模型]**：AI 成功給出分配建議
- **[本地演算法]**：降級到本地演算法進行分配

## 模型選擇

| 模型 | 用途 | 特性 |
|------|------|------|
| mistral | 派發 | 輕量(7.3B)，速度快 |
| neural-chat | 偵錯 | 對話優化，驗證準確 |

可根據需求在 `.env` 中調整。其他推薦模型：`llama2`, `orca-mini`, `openchat`

## 故障排查

### Ollama 連線失敗
```
無法連線到 Ollama，將使用本地演算法降級
```
**解決**：確保 Ollama 服務正在運行（`ollama serve`）

### 模型未找到
```
Model 'mistral' not found
```
**解決**：執行 `ollama pull mistral` 下載模型

## 性能提示

- Ollama 首次運行會載入模型，可能較慢
- 建議使用 GPU 加速（Ollama 會自動使用）
- 如需更快的推理，可改用量化模型如 `mistral-7b-q4`

## 延伸閱讀

詳見 `docs/SPECIFICATION.md` 瞭解架構、API 規格與本地演算法細節。 