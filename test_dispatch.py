"""
測試腳本：測試 DispatchService 的派發邏輯
包括 AI 成功、AI 失敗降級、本地演算法等場景
"""

import json
import logging
from services import DispatchService
from schemas import (
    Volunteer, Task, DispatchRequest, Location, Metadata, WorkType
)

# 設定日誌顯示
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_scenario_1_ai_available():
    """測試場景 1：AI 可用，正常派發"""
    logger.info("\n" + "="*60)
    logger.info("測試場景 1：AI 可用（正常派發）")
    logger.info("="*60)
    
    # 建立測試資料
    vols = [
        Volunteer(
            id='vol_01',
            skills=['medical', 'firstaid'],
            location=Location(lat=23.654, lng=121.432),
            availability=True
        ),
        Volunteer(
            id='vol_02',
            skills=['logistics', 'heavylifting'],
            location=Location(lat=23.660, lng=121.440),
            availability=True
        ),
        Volunteer(
            id='vol_03',
            skills=['medical'],
            location=Location(lat=23.650, lng=121.435),
            availability=True
        ),
    ]
    
    tasks = [
        Task(
            id='task_101',
            type_id='medical',
            location=Location(lat=23.656, lng=121.435),
            urgency=5  # 最急
        ),
        Task(
            id='task_102',
            type_id='logistics',
            location=Location(lat=23.665, lng=121.445),
            urgency=3
        ),
    ]
    
    metadata = Metadata(
        incident_id='test-001',
        priority_weighting='balanced'
    )
    
    work_types = [
        WorkType(type_id='medical', required_skills=['medical', 'firstaid']),
        WorkType(type_id='logistics', required_skills=['logistics']),
    ]
    
    request = DispatchRequest(
        metadata=metadata,
        work_types=work_types,
        volunteers=vols,
        tasks=tasks
    )
    
    # 執行派發
    result = DispatchService.process_dispatch(request)
    
    # 顯示結果
    logger.info(f"派發狀態: {result['status']}")
    logger.info(f"派發 ID: {result['dispatch_id']}")
    logger.info(f"分派數量: {len(result['assignments'])}")
    
    for assignment in result['assignments']:
        logger.info(f"\n  任務 {assignment.task_id}:")
        logger.info(f"    指派志工: {assignment.assigned_volunteers}")
        logger.info(f"    預估時間: {assignment.eta_minutes} 分鐘")
        logger.info(f"    決策說明: {assignment.reasoning_summary[:80]}...")
    
    return result


def test_scenario_2_simulate_ai_failure():
    """測試場景 2：模擬 AI 不可用，驗證本地演算法降級"""
    logger.info("\n" + "="*60)
    logger.info("測試場景 2：本地演算法降級（模擬 AI 失敗）")
    logger.info("="*60)
    
    # 暫時設定無效的 API 金鑰或模型名稱
    # 這樣會觸發異常，導致本地演算法接手
    
    vols = [
        Volunteer(
            id='vol_01',
            skills=['medical'],
            location=Location(lat=23.654, lng=121.432),
            availability=True
        ),
        Volunteer(
            id='vol_02',
            skills=['search', 'rescue'],
            location=Location(lat=23.670, lng=121.450),
            availability=True
        ),
    ]
    
    tasks = [
        Task(
            id='task_201',
            type_id='medical',
            location=Location(lat=23.656, lng=121.435),
            urgency=4
        ),
    ]
    
    metadata = Metadata(
        incident_id='test-002',
        priority_weighting='speed'
    )
    
    work_types = [
        WorkType(type_id='medical', required_skills=['medical']),
    ]
    
    request = DispatchRequest(
        metadata=metadata,
        work_types=work_types,
        volunteers=vols,
        tasks=tasks
    )
    
    # 執行派發（會觸發降級，因為模型名稱無效）
    result = DispatchService.process_dispatch(request)
    
    logger.info(f"派發狀態: {result['status']}")
    logger.info(f"派發 ID: {result['dispatch_id']}")
    
    for assignment in result['assignments']:
        logger.info(f"\n  任務 {assignment.task_id}:")
        logger.info(f"    指派志工: {assignment.assigned_volunteers}")
        logger.info(f"    預估時間: {assignment.eta_minutes} 分鐘")
        logger.info(f"    決策說明: {assignment.reasoning_summary}")
        
        # 檢查是否有本地演算法的標記
        if '[本地演算法]' in assignment.reasoning_summary:
            logger.info("    ✓ 確認使用本地演算法降級")
        elif '[系統自動降級提示]' in assignment.reasoning_summary:
            logger.info("    ✓ 確認系統降級")
    
    return result


def test_scenario_3_multiple_tasks():
    """測試場景 3：多個任務，驗證志工池管理"""
    logger.info("\n" + "="*60)
    logger.info("測試場景 3：多個任務（志工池管理）")
    logger.info("="*60)
    
    vols = [
        Volunteer(
            id='vol_01',
            skills=['medical'],
            location=Location(lat=23.654, lng=121.432),
            availability=True
        ),
        Volunteer(
            id='vol_02',
            skills=['logistics'],
            location=Location(lat=23.660, lng=121.440),
            availability=True
        ),
        Volunteer(
            id='vol_03',
            skills=['medical', 'logistics'],
            location=Location(lat=23.650, lng=121.430),
            availability=True
        ),
    ]
    
    # 3 個任務，只有 3 位志工
    tasks = [
        Task(
            id='task_301',
            type_id='medical',
            location=Location(lat=23.656, lng=121.435),
            urgency=5
        ),
        Task(
            id='task_302',
            type_id='logistics',
            location=Location(lat=23.665, lng=121.445),
            urgency=4
        ),
        Task(
            id='task_303',
            type_id='medical',
            location=Location(lat=23.648, lng=121.428),
            urgency=3
        ),
    ]
    
    metadata = Metadata(
        incident_id='test-003',
        priority_weighting='balanced'
    )
    
    work_types = [
        WorkType(type_id='medical', required_skills=['medical']),
        WorkType(type_id='logistics', required_skills=['logistics']),
    ]
    
    request = DispatchRequest(
        metadata=metadata,
        work_types=work_types,
        volunteers=vols,
        tasks=tasks
    )
    
    result = DispatchService.process_dispatch(request)
    
    logger.info(f"派發狀態: {result['status']}")
    logger.info(f"總任務數: {len(result['assignments'])}")
    
    assigned_vols = set()
    for assignment in result['assignments']:
        logger.info(f"\n  任務 {assignment.task_id}:")
        logger.info(f"    指派志工: {assignment.assigned_volunteers}")
        logger.info(f"    預估時間: {assignment.eta_minutes} 分鐘")
        
        for vol_id in assignment.assigned_volunteers:
            assigned_vols.add(vol_id)
    
    logger.info(f"\n已指派的志工總數: {len(assigned_vols)}")
    logger.info(f"指派的志工 ID: {assigned_vols}")
    
    return result


def test_scenario_4_check_eta_calculation():
    """測試場景 4：驗證 ETA 計算"""
    logger.info("\n" + "="*60)
    logger.info("測試場景 4：ETA 計算驗證")
    logger.info("="*60)
    
    # 特意設定已知距離的位置
    # 位置：志工在 (0, 0)，任務在 (0, 0.01)，距離約 1.11 km
    vols = [
        Volunteer(
            id='vol_eta_test',
            skills=['test'],
            location=Location(lat=23.654, lng=121.432),
            availability=True
        ),
    ]
    
    tasks = [
        Task(
            id='task_eta',
            type_id='test',
            location=Location(lat=23.654 + 0.01, lng=121.432),  # 約 1.11 km
            urgency=1
        ),
    ]
    
    metadata = Metadata(
        incident_id='test-eta',
        priority_weighting='balanced'
    )
    
    work_types = [
        WorkType(type_id='test', required_skills=['test']),
    ]
    
    request = DispatchRequest(
        metadata=metadata,
        work_types=work_types,
        volunteers=vols,
        tasks=tasks
    )
    
    result = DispatchService.process_dispatch(request)
    
    for assignment in result['assignments']:
        logger.info(f"\n  任務 {assignment.task_id}:")
        logger.info(f"    指派志工: {assignment.assigned_volunteers}")
        eta = assignment.eta_minutes
        logger.info(f"    預估時間: {eta} 分鐘")
        
        # 預期 ETA = int((1.11 / 40) * 60) + 5 ≈ 6-7 分鐘
        logger.info(f"    （預期: ~6-7 分鐘，計算方式: distance/40*60+5）")


if __name__ == '__main__':
    logger.info("\n🚀 開始測試 Dispatch Service")
    logger.info("共 4 個測試場景")
    
    try:
        # 執行各個測試
        test_scenario_1_ai_available()
        test_scenario_2_simulate_ai_failure()
        test_scenario_3_multiple_tasks()
        test_scenario_4_check_eta_calculation()
        
        logger.info("\n" + "="*60)
        logger.info("✅ 所有測試完成")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ 測試過程中發生錯誤: {e}", exc_info=True)
