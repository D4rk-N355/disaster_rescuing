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

# 測試用預留根路由
@app.get("/")
def read_root():
    return {"message": "Disaster Volunteer Dispatcher API is running."}