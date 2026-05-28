from fastapi import FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from schemas import DispatchRequest, DispatchResponse
from services import DispatchService

app = FastAPI(
    title="救災志工智慧分配 API Component",
    description="數位發展部 - 防災積木元件創新賽參賽作品",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# 1. 核心 API 運作端點 (派發任務)
# ---------------------------------------------------------------------------
@app.post("/api/v1/dispatch/v1", response_model=DispatchResponse, status_code=status.HTTP_200_OK)
async def create_dispatch_plan(payload: DispatchRequest):
    try:
        # 呼叫獨立的 Service 模組處理業務邏輯
        result = DispatchService.process_dispatch(payload)
        return JSONResponse(content=jsonable_encoder(result))
        
    except ValueError as val_err:
        # 處理資料格式正確但內容不合規的狀況 (422)
        raise HTTPException(status_code=422, detail=f"資料處理異常: {str(val_err)}")
    except Exception as e:
        # 伺服器內部錯誤 (500)
        raise HTTPException(status_code=500, detail=f"AI 分配服務暫時無法使用: {str(e)}")


# ---------------------------------------------------------------------------
# 2. 健康檢查端點 (含 Ollama 連線狀態)
# ---------------------------------------------------------------------------
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    系統健康檢查端點，同時確認本機 API 與後端 Ollama 服務的運作狀態。
    """
    # 呼叫 Service 內寫好的 Ollama 連線檢查方法
    ollama_healthy = DispatchService._verify_ollama_connection()
    
    status_msg = "healthy" if ollama_healthy else "degraded"
    
    # 即使 Ollama 斷線，因為系統有「本地演算法」作為降級備援(Fallback)，
    # 這裡可以選擇不噴 500 錯誤，而是回傳狀態讓監控系統知道。
    return {
        "status": status_msg,
        "components": {
            "api_server": "up",
            "ollama_service": "up" if ollama_healthy else "down"
        }
    }


# 測試用預留根路由
@app.get("/")
def read_root():
    return {"message": "Disaster Volunteer Dispatcher API is running."}