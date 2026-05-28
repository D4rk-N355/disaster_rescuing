import os
import math
import uuid
import json
import logging
import requests
from typing import List, Dict
from collections import defaultdict
from dotenv import load_dotenv
from schemas import DispatchRequest, Assignment, Volunteer, Task

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


class DispatchService:
    BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    DISPATCH_MODEL = os.getenv('OLLAMA_MODEL_DISPATCH', 'mistral')
    DEBUG_MODEL = os.getenv('OLLAMA_MODEL_DEBUG', 'neural-chat')
    GENERATE_ENDPOINT = f"{BASE_URL}/api/generate"

    @staticmethod
    def _verify_ollama_connection():
        try:
            response = requests.get(f"{DispatchService.BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                logging.info(f"✅ 成功連線到 Ollama: {DispatchService.BASE_URL}")
                return True
            else:
                logging.warning(f"⚠️ Ollama 連線失敗 (狀態碼: {response.status_code})")
                return False
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"⚠️ 無法連線到 Ollama ({DispatchService.BASE_URL}): {e}")
            logging.info("📍 請確認 Tailscale 網路是否正常且 Ollama 伺服器正在運行")
            return False
        except Exception as e:
            logging.error(f"❌ Ollama 連線檢查錯誤: {e}")
            return False

    @staticmethod
    def calculate_distance(loc1, loc2) -> float:
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
        return [v for v in volunteers if v.availability]

    @classmethod
    def _call_ollama(cls, model: str, prompt: str) -> str:
        try:
            logging.info(f"調用 Ollama 模型 {model} (伺服器: {cls.BASE_URL})")
            payload = {"model": model, "prompt": prompt, "stream": False}
            response = requests.post(cls.GENERATE_ENDPOINT, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json().get('response', '')
                logging.info(f"✅ 模型 {model} 成功回應")
                return result
            else:
                logging.error(f"❌ Ollama API 錯誤 (狀態碼: {response.status_code}): {response.text}")
                raise Exception(f"Ollama API 返回狀態碼 {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            logging.error(f"❌ 無法連線到 Ollama ({cls.BASE_URL}): {e}")
            raise
        except requests.exceptions.Timeout:
            logging.error(f"⏱️ Ollama 請求超時 (超過 30 秒)")
            raise
        except Exception as e:
            logging.error(f"❌ Ollama 調用失敗: {e}")
            raise

    @classmethod
    def call_ai_agent_layer(cls, available_vols: List[Volunteer], tasks: List[Task], weighting: str) -> List[Assignment]:
        assignments: List[Assignment] = []

        def local_assign(task: Task, vols: List[Volunteer]) -> Assignment:
            if not vols:
                return Assignment(task_id=task.id, assigned_volunteers=[], eta_minutes=0, reasoning_summary="[本地演算法] 無可用志工")
            
            best = None
            best_dist = float('inf')
            for v in vols:
                d = cls.calculate_distance(v.location, task.location)
                if d < best_dist:
                    best_dist = d
                    best = v

            eta = int((best_dist / 40) * 60) + 5 if best else 0
            return Assignment(task_id=task.id, assigned_volunteers=[best.id] if best else [], eta_minutes=eta,
                            reasoning_summary=f"[本地演算法] 指派 {best.id if best else '無'}，距離 {best_dist:.1f}km")

        # 先檢查 Ollama 是否可用
        ollama_available = cls._verify_ollama_connection()

        for task in sorted(tasks, key=lambda x: x.urgency, reverse=True):
            vols_info = ', '.join([f"{v.id}({v.skills})" for v in available_vols])
            prompt = f"任務ID: {task.id}, 類型: {task.type_id}, 緊急度: {task.urgency}/5\n可用志工: {vols_info}\n請指派最合適的志工ID，並說明理由。"

            if not ollama_available:
                logging.info(f"⚠️ Ollama 不可用，使用本地演算法派發任務 {task.id}")
                fallback = local_assign(task, available_vols)
                assignments.append(fallback)
                if fallback.assigned_volunteers:
                    available_vols = [v for v in available_vols if v.id not in fallback.assigned_volunteers]
                continue

            try:
                # 嘗試使用派發模型
                logging.info(f"📍 使用派發模型 ({cls.DISPATCH_MODEL}) 處理任務 {task.id}")
                response = cls._call_ollama(cls.DISPATCH_MODEL, prompt)
                
                # 簡單的解析 - 從回應中提取志工 ID
                assigned_id = None
                for vol in available_vols:
                    if vol.id in response:
                        assigned_id = vol.id
                        break
                
                if assigned_id:
                    logging.info(f"✅ 派發模型建議: 指派 {assigned_id} 給任務 {task.id}")
                    # 計算 ETA
                    eta_final = 15
                    for vol in available_vols:
                        if vol.id == assigned_id:
                            dist = cls.calculate_distance(vol.location, task.location)
                            eta_final = int((dist / 40) * 60) + 5
                    
                    assignments.append(Assignment(
                        task_id=task.id,
                        assigned_volunteers=[assigned_id],
                        eta_minutes=eta_final,
                        reasoning_summary=f"[Ollama-派發] {response[:100]}"
                    ))
                    available_vols = [v for v in available_vols if v.id != assigned_id]
                else:
                    logging.warning(f"⚠️ 派發模型回應無有效志工ID，嘗試調用偵錯模型")
                    # 嘗試偵錯模型
                    try:
                        debug_response = cls._call_ollama(cls.DEBUG_MODEL, f"前面的派發結果無效。{prompt}")
                        for vol in available_vols:
                            if vol.id in debug_response:
                                assigned_id = vol.id
                                break
                        
                        if assigned_id:
                            logging.info(f"✅ 偵錯模型建議: 指派 {assigned_id} 給任務 {task.id}")
                            eta_final = 15
                            for vol in available_vols:
                                if vol.id == assigned_id:
                                    dist = cls.calculate_distance(vol.location, task.location)
                                    eta_final = int((dist / 40) * 60) + 5
                            
                            assignments.append(Assignment(
                                task_id=task.id,
                                assigned_volunteers=[assigned_id],
                                eta_minutes=eta_final,
                                reasoning_summary=f"[Ollama-偵錯] {debug_response[:100]}"
                            ))
                            available_vols = [v for v in available_vols if v.id != assigned_id]
                        else:
                            raise Exception("偵錯模型也無法提供有效建議")
                    except Exception as debug_e:
                        logging.warning(f"⚠️ 偵錯模型失敗: {debug_e}，使用本地演算法")
                        fallback = local_assign(task, available_vols)
                        assignments.append(fallback)
                        if fallback.assigned_volunteers:
                            available_vols = [v for v in available_vols if v.id not in fallback.assigned_volunteers]

            except Exception as e:
                logging.error(f"❌ Ollama 派發失敗: {e}，降級使用本地演算法")
                fallback = local_assign(task, available_vols)
                assignments.append(fallback)
                if fallback.assigned_volunteers:
                    available_vols = [v for v in available_vols if v.id not in fallback.assigned_volunteers]

        return assignments

    @classmethod
    def process_dispatch(cls, request: DispatchRequest):
        active_vols = cls.filter_available_volunteers(request.volunteers)
        assignments = cls.call_ai_agent_layer(available_vols=active_vols, tasks=request.tasks, weighting=request.metadata.priority_weighting)
        return {"status": "success", "dispatch_id": str(uuid.uuid4()), "assignments": assignments}


logging.info(f"🚀 Dispatch Service 初始化完成")
logging.info(f"📍 Ollama 伺服器: {DispatchService.BASE_URL}")
logging.info(f"🤖 派發模型: {DispatchService.DISPATCH_MODEL}")
logging.info(f"🔍 偵錯模型: {DispatchService.DEBUG_MODEL}")
DispatchService._verify_ollama_connection()
