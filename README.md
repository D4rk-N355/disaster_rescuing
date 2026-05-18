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

### A. 輸入規格 (Input JSON Schema)
- `metadata`: 包含事件 ID 與調度權重模式（如：平衡、速度優先、專長優先）。
- [cite_start]`work_types`: 定義現場的基本工作類型與所需專長標籤 [cite: 64]。
- [cite_start]`volunteers`: 包含可用志工的 ID、專長標籤、目前經緯度與可用狀態 [cite: 64]。
- [cite_start]`tasks`: 待處理的災情任務，包含地點與緊急程度（1-5 級） [cite: 64]。

### B. 輸出規格 (Output JSON Schema)
- `dispatch_id`: 該批次調度的唯一識別碼。
- [cite_start]`assignments`: 分配結果清單，包含任務 ID、指派志工 ID、預估抵達時間（ETA）與 **AI 決策推理摘要** [cite: 45, 64]。

---

## 4. 快速開始與環境需求 (Quick Start)

### 系統環境要求
- [cite_start]Python 版本：`Python 3.9` 或更新版本 。

### 步驟 1：安裝依賴套件
pip install -r requirements.txt

### 步驟 2：配置環境變數
在專案根目錄下建立 .env 檔案，並填入向 Google AI Studio 申請的免費金鑰：

程式碼片段
GEMINI_API_KEY=your_gemini_api_key_here

### 步驟 3：啟動本地 API 服務
uvicorn main:app --reload
啟動後，可開啟 http://127.0.0.1:8000/docs 查看自動生成的 OpenAPI (Swagger) 規格文件

5. Client Sample Code (API 呼叫範例)
以下提供其他積木元件（如通報元件）呼叫本分析 API 的測試範例 ：
import requests

url = "[http://127.0.0.1:8000/api/v1/dispatch/v1](http://127.0.0.1:8000/api/v1/dispatch/v1)"
payload = {
  "metadata": {
    "incident_id": "mataian-2025-001",
    "priority_weighting": "balanced"
  },
  "work_types": [
    {"type_id": "Medical", "required_skills": ["EMT", "FirstAid"]},
    {"type_id": "Logistics", "required_skills": ["HeavyLifting"]}
  ],
  "volunteers": [
    {
      "id": "vol_01",
      "skills": ["FirstAid"],
      "location": {"lat": 23.654, "lng": 121.432},
      "availability": True
    },
    {
      "id": "vol_02",
      "skills": ["HeavyLifting"],
      "location": {"lat": 23.660, "lng": 121.440},
      "availability": True
    }
  ],
  "tasks": [
    {
      "id": "task_101",
      "type_id": "Medical",
      "location": {"lat": 23.656, "lng": 121.435},
      "urgency": 5
    }
  ]
}

response = requests.post(url, json=payload)
print(response.json())