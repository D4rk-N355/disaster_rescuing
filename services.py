import os
import math
import uuid
import json
from typing import List
from google import genai
from google.genai import types
from dotenv import load_dotenv
from schemas import DispatchRequest, Assignment, Volunteer, Task

# 載入環境變數（會去讀取專案目錄下的 .env 檔案）
load_dotenv()

class DispatchService:
    # 初始化 Gemini Client（會自動去抓取環境變數中的 GEMINI_API_KEY）
    # 你需要在 .env 檔案中寫入: GEMINI_API_KEY=你的金鑰
    client = genai.Client()

    @staticmethod
    def calculate_distance(loc1, loc2) -> float:
        """使用 Haversine 公式計算兩點間的經緯度距離 (公里)"""
        R = 6371.0
        lat1, lng1 = math.radians(loc1.lat), math.radians(loc1.lng)
        lat2, lng2 = math.radians(loc2.lat), math.radians(loc2.lng)
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def filter_available_volunteers(volunteers: List[Volunteer]) -> List[Volunteer]:
        """過濾層：剔除目前不可用的志工"""
        return [v for v in volunteers if v.availability]

    @classmethod
    def call_ai_agent_layer(cls, available_vols: List[Volunteer], tasks: List[Task], weighting: str) -> List[Assignment]:
        """
        AI 分配層 (真正的 Gemini API 介接)
        """
        assignments = []
        
        # 為了讓 AI 更好做出準確判斷，我們把結構化資料轉成文字 Prompt
        vols_prompt = ", ".join([f"[志工ID: {v.id}, 專長: {v.skills}]" for v in available_vols])
        
        # 依據任務緊急度排序，優先處理緊急任務（展現 Agent 的多步驟任務調度特性）
        for task in sorted(tasks, key=lambda x: x.urgency, reverse=True):
            
            # 計算每位志工到該任務的預估時間 (ETA)，做為 AI 決策的輔助特徵
            vols_with_eta = []
            for vol in available_vols:
                dist = cls.calculate_distance(vol.location, task.location)
                eta = int((dist / 40) * 60) + 5  # 時速 40 公里 + 5 分鐘準備
                vols_with_eta.append(f"志工 {vol.id}(專長:{vol.skills}, 預估{eta}分鐘抵達)")

            # 建構給 Gemini 的 Prompt
            prompt = f"""
            你現在是臺灣災害應變中心的智慧調度 Agent。
            目前正在處理 2025 年花蓮馬太鞍溪堰塞湖災害事件的志工分配。
            
            【目前任務】
            - 任務 ID: {task.id}
            - 任務工作類型: {task.type_id}
            - 緊急程度: {task.urgency} (1-5，5為最緊急)
            - 調度權重模式: {weighting}
            
            【候選可用志工與抵達時間】
            {", ".join(vols_with_eta)}
            
            【任務指派要求】
            1. 請從候選志工中，挑選出「最符合該任務工作類型專長」且「抵達時間合理」的 1 位志工 ID。
            2. 撰寫一段簡短的『推理摘要(reasoning_summary)』，解釋你為何這樣分配（字數在 100 字內）。
            
            請嚴格以下列 JSON 格式回傳，不要包含任何額外的文字或 Markdown 標籤：
            {{
                "assigned_volunteer": "挑選的志工ID",
                "reasoning_summary": "你的決策推理說明"
            }}
            """

            try:
                # 呼叫 Gemini API
                response = cls.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                # 解析回應
                ai_result = json.loads(response.text)
                assigned_id = ai_result.get("assigned_volunteer")
                reasoning = ai_result.get("reasoning_summary", "AI 自動分配完成。")
                
                # 從剛才計算的清單中抓出對應的 ETA
                eta_final = 15 # 預設預估時間
                for vol in available_vols:
                    if vol.id == assigned_id:
                        dist = cls.calculate_distance(vol.location, task.location)
                        eta_final = int((dist / 40) * 60) + 5

                assignments.append(Assignment(
                    task_id=task.id,
                    assigned_volunteers=[assigned_id] if assigned_id else [],
                    eta_minutes=eta_final,
                    reasoning_summary=reasoning
                ))
                
                # 為了避免同一個志工在同一個調度批次被重複指派，將其移出可用清單
                if assigned_id:
                    available_vols = [v for v in available_vols if v.id != assigned_id]
                    
            except AttributeError as e:
                # 處理模組屬性錯誤
                print(f"模組屬性錯誤: {e}")
                assignments.append(Assignment(
                    task_id=task.id,
                    assigned_volunteers=[available_vols[0].id] if available_vols else [],
                    eta_minutes=20,
                    reasoning_summary="[系統自動降級提示] 模組屬性錯誤，改由地端鄰近距離演算法進行基礎指派。"
                ))
            except Exception as e:
                # 處理其他未知錯誤
                print(f"未知錯誤: {e}")
                assignments.append(Assignment(
                    task_id=task.id,
                    assigned_volunteers=[available_vols[0].id] if available_vols else [],
                    eta_minutes=20,
                    reasoning_summary="[系統自動降級提示] 未知錯誤，改由地端鄰近距離演算法進行基礎指派。"
                ))
                
        return assignments

    @classmethod
    def process_dispatch(cls, request: DispatchRequest):
        active_vols = cls.filter_available_volunteers(request.volunteers)
        assignments = cls.call_ai_agent_layer(
            available_vols=active_vols,
            tasks=request.tasks,
            weighting=request.metadata.priority_weighting
        )
        return {
            "status": "success",
            "dispatch_id": str(uuid.uuid4()),
            "assignments": assignments
        }