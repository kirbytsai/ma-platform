"""
提案管理 API 端點 - 完整模組化版本
整合所有模組化的提案服務，提供完整的 REST API
支援 30+ 個功能：CRUD、工作流程、搜尋、管理員功能、測試端點
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status, UploadFile, File
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessException, ValidationException, PermissionDeniedException
from app.models.user import UserRole
from app.models.proposal import ProposalStatus, Industry, CompanySize
from app.schemas.proposal import (
    ProposalCreate, ProposalUpdate, ProposalResponse, 
    ProposalSearchParams, ProposalSubmitRequest,
    ProposalApproveRequest, ProposalRejectRequest,
    ProposalListResponse, ProposalStatistics
)

# 🔥 使用真正的模組化服務！
from app.services.proposal import ProposalService
from app.api.deps import (
    get_current_user, require_roles, require_admin,
    PaginationParams, get_current_user_optional
)

router = APIRouter()

# 創建模組化提案服務實例
proposal_service = ProposalService()


# ==================== 模組化測試端點 ====================

@router.get("/test/modules")
async def test_all_modules():
    """測試所有模組化服務是否正常載入"""
    try:
        modules_status = {
            "validation_service": hasattr(proposal_service, 'validation') and proposal_service.validation is not None,
            "core_service": hasattr(proposal_service, 'core') and proposal_service.core is not None,
            "workflow_service": hasattr(proposal_service, 'workflow') and proposal_service.workflow is not None,
            "search_service": hasattr(proposal_service, 'search') and proposal_service.search is not None,
            "admin_service": hasattr(proposal_service, 'admin') and proposal_service.admin is not None,
            "main_service": isinstance(proposal_service, type(proposal_service))
        }
        
        all_loaded = all(modules_status.values())
        
        return {
            "success": True,
            "message": "模組化服務測試完成",
            "modules_loaded": modules_status,
            "all_modules_loaded": all_loaded,
            "total_modules": 6,
            "loaded_modules": sum(modules_status.values()),
            "architecture": "完整模組化架構",
            "version": "2.0.0",
            "details": {
                "validation_service": "資料驗證和權限檢查",
                "core_service": "基礎 CRUD 操作",
                "workflow_service": "狀態流轉管理",
                "search_service": "搜尋和篩選功能",
                "admin_service": "管理員專用功能",
                "main_service": "統一入口服務"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"模組載入測試失敗: {str(e)}",
            "error": str(e),
            "suggestion": "請檢查模組化服務的初始化"
        }


@router.get("/test/features")
async def test_features():
    """展示所有可用功能列表"""
    return {
        "success": True,
        "message": "M&A 平台提案管理系統 - 完整功能列表",
        "features": {
            "core_crud": [
                "create_proposal - 創建提案",
                "get_proposal_by_id - 取得提案詳情", 
                "update_proposal - 更新提案",
                "delete_proposal - 刪除提案",
                "get_proposals_by_creator - 取得創建者提案列表",
                "add_proposal_file - 添加提案附件",
                "remove_proposal_file - 移除提案附件"
            ],
            "workflow_management": [
                "submit_proposal - 提交審核",
                "withdraw_proposal - 撤回提案",
                "publish_proposal - 發布提案",
                "archive_proposal - 歸檔提案",
                "get_workflow_history - 取得工作流程歷史",
                "check_transition_permission - 檢查狀態轉換權限"
            ],
            "search_engine": [
                "search_proposals - 智能搜尋",
                "full_text_search - 全文搜尋",
                "filter_by_industry - 產業篩選",
                "filter_by_size - 公司規模篩選",
                "filter_by_location - 地區篩選",
                "filter_by_status - 狀態篩選",
                "get_search_statistics - 搜尋統計",
                "advanced_search - 進階搜尋"
            ],
            "admin_functions": [
                "approve_proposal - 審核通過",
                "reject_proposal - 審核拒絕",
                "batch_approve - 批量通過",
                "batch_reject - 批量拒絕",
                "get_pending_reviews - 取得待審核列表",
                "get_proposal_statistics - 提案統計",
                "get_admin_dashboard - 管理員儀表板"
            ],
            "validation_system": [
                "check_creator_permission - 檢查創建權限",
                "check_view_permission - 檢查查看權限",
                "validate_proposal_data - 驗證提案資料",
                "validate_status_transition - 驗證狀態轉換"
            ]
        },
        "total_functions": 30,
        "module_count": 6,
        "architecture": "模組化 + 統一接口",
        "testing_endpoints": [
            "GET /api/v1/proposals/test/modules - 模組測試",
            "GET /api/v1/proposals/test/features - 功能列表"
        ]
    }


# ==================== 基礎 CRUD 端點 ====================

@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_proposal(
    proposal_data: ProposalCreate,
    current_user = Depends(require_roles([UserRole.SELLER, UserRole.ADMIN]))
):
    """
    創建新提案 - 模組化版本
    
    - **需要權限**: 提案方或管理員
    - **功能**: 創建新的提案，初始狀態為草稿
    - **模組**: ProposalCoreService.create_proposal()
    """
    try:
        proposal = await proposal_service.create_proposal(
            creator_id=str(current_user.id),
            proposal_data=proposal_data
        )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": "提案創建成功",
                "data": {
                    "proposal_id": str(proposal.id),
                    "status": proposal.status,
                    "company_name": proposal.company_info.company_name,
                    "created_at": proposal.created_at.isoformat(),
                    "creator_id": str(proposal.creator_id)
                },
                "module_info": {
                    "service": "ProposalCoreService",
                    "method": "create_proposal",
                    "version": "2.0.0 - 模組化版本"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量審核時發生錯誤: {str(e)}")


@router.post("/admin/batch-reject")
async def batch_reject_proposals(
    proposal_ids: List[str] = Body(..., description="提案 ID 列表"),
    reason: str = Body(..., description="批量拒絕原因"),
    current_user = Depends(require_admin)
):
    """
    批量審核拒絕 - 模組化版本
    
    - **需要權限**: 管理員
    - **功能**: 批量審核拒絕多個提案
    - **模組**: ProposalAdminService.batch_reject()
    """
    try:
        results = await proposal_service.admin.batch_reject(
            proposal_ids=proposal_ids,
            admin_id=str(current_user.id),
            reason=reason
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"批量拒絕完成，成功: {results['success_count']}，失敗: {results['failed_count']}",
                "data": results,
                "module_info": {
                    "service": "ProposalAdminService",
                    "method": "batch_reject"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量拒絕時發生錯誤: {str(e)}")


@router.get("/admin/statistics")
async def get_proposal_statistics(
    start_date: Optional[datetime] = Query(None, description="開始日期"),
    end_date: Optional[datetime] = Query(None, description="結束日期"),
    current_user = Depends(require_admin)
):
    """
    取得提案統計 - 模組化版本
    
    - **需要權限**: 管理員
    - **功能**: 取得提案的各種統計資訊
    - **模組**: ProposalAdminService.get_proposal_statistics()
    """
    try:
        stats = await proposal_service.admin.get_proposal_statistics(start_date, end_date)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": stats,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "module_info": {
                    "service": "ProposalAdminService",
                    "method": "get_proposal_statistics"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計資訊時發生錯誤: {str(e)}")


@router.get("/admin/dashboard")
async def get_admin_dashboard(
    current_user = Depends(require_admin)
):
    """
    管理員儀表板 - 模組化版本
    
    - **需要權限**: 管理員
    - **功能**: 取得管理員儀表板的完整資訊
    - **模組**: ProposalAdminService.get_admin_dashboard()
    """
    try:
        dashboard_data = await proposal_service.admin.get_admin_dashboard()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": dashboard_data,
                "module_info": {
                    "service": "ProposalAdminService",
                    "method": "get_admin_dashboard"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得管理員儀表板時發生錯誤: {str(e)}")


# ==================== 檔案管理端點 ====================

@router.post("/{proposal_id}/files")
async def add_proposal_file(
    proposal_id: str,
    file: UploadFile = File(...),
    description: Optional[str] = Body(None, description="檔案描述"),
    current_user = Depends(get_current_user)
):
    """
    添加提案附件 - 模組化版本
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 上傳並添加提案相關檔案
    - **模組**: ProposalCoreService.add_proposal_file()
    """
    try:
        # 檔案驗證
        if file.size > 10 * 1024 * 1024:  # 10MB 限制
            raise HTTPException(status_code=400, detail="檔案大小不能超過 10MB")
        
        allowed_types = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png']
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_types:
            raise HTTPException(status_code=400, detail=f"不支援的檔案類型: {file_extension}")
        
        # 讀取檔案內容
        file_content = await file.read()
        
        file_info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(file_content),
            "description": description,
            "content": file_content
        }
        
        success = await proposal_service.add_proposal_file(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            file_info=file_info
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="添加檔案失敗")
        
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "message": "檔案添加成功",
                "file_info": {
                    "filename": file.filename,
                    "size": len(file_content),
                    "content_type": file.content_type,
                    "description": description
                },
                "module_info": {
                    "service": "ProposalCoreService",
                    "method": "add_proposal_file"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加檔案時發生錯誤: {str(e)}")


@router.delete("/{proposal_id}/files/{file_id}")
async def remove_proposal_file(
    proposal_id: str,
    file_id: str,
    current_user = Depends(get_current_user)
):
    """
    移除提案附件 - 模組化版本
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 移除提案的附件檔案
    - **模組**: ProposalCoreService.remove_proposal_file()
    """
    try:
        success = await proposal_service.remove_proposal_file(
            proposal_id=proposal_id,
            file_id=file_id,
            user_id=str(current_user.id)
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="移除檔案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "檔案移除成功",
                "module_info": {
                    "service": "ProposalCoreService",
                    "method": "remove_proposal_file"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移除檔案時發生錯誤: {str(e)}")


# ==================== 進階搜尋端點 ====================

@router.post("/search/advanced")
async def advanced_search(
    search_criteria: Dict[str, Any] = Body(..., description="進階搜尋條件"),
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    進階搜尋 - 模組化版本
    
    - **權限**: 公開搜尋，登入用戶可看更多內容
    - **功能**: 支援複雜的搜尋條件組合
    - **模組**: ProposalSearchService.advanced_search()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.advanced_search(
            search_criteria, page, limit, user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "search_criteria": search_criteria,
                "module_info": {
                    "service": "ProposalSearchService",
                    "method": "advanced_search"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"進階搜尋時發生錯誤: {str(e)}")


@router.get("/search/filter/industry/{industry}")
async def filter_by_industry(
    industry: Industry,
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    按產業篩選 - 模組化版本
    
    - **權限**: 公開篩選
    - **功能**: 篩選特定產業的提案
    - **模組**: ProposalSearchService.filter_by_industry()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.filter_by_industry(
            industry, page, limit, user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "filter": {
                    "industry": industry,
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "service": "ProposalSearchService",
                    "method": "filter_by_industry"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產業篩選時發生錯誤: {str(e)}")


@router.get("/search/filter/size/{company_size}")
async def filter_by_size(
    company_size: CompanySize,
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    按公司規模篩選 - 模組化版本
    
    - **權限**: 公開篩選
    - **功能**: 篩選特定規模的公司提案
    - **模組**: ProposalSearchService.filter_by_size()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.filter_by_size(
            company_size, page, limit, user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "filter": {
                    "company_size": company_size,
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "service": "ProposalSearchService",
                    "method": "filter_by_size"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"公司規模篩選時發生錯誤: {str(e)}")


@router.get("/search/filter/location/{location}")
async def filter_by_location(
    location: str,
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    按地區篩選 - 模組化版本
    
    - **權限**: 公開篩選
    - **功能**: 篩選特定地區的提案
    - **模組**: ProposalSearchService.filter_by_location()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.filter_by_location(
            location, page, limit, user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "filter": {
                    "location": location,
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "service": "ProposalSearchService",
                    "method": "filter_by_location"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"地區篩選時發生錯誤: {str(e)}")


# ==================== 驗證系統端點 ====================

@router.get("/{proposal_id}/permissions")
async def check_proposal_permissions(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    檢查提案權限 - 模組化版本
    
    - **需要權限**: 已登入用戶
    - **功能**: 檢查當前用戶對提案的各種權限
    - **模組**: ProposalValidationService
    """
    try:
        permissions = {
            "can_view": await proposal_service.validation.check_view_permission(
                proposal_id, str(current_user.id)
            ),
            "can_edit": await proposal_service.validation.check_edit_permission(
                proposal_id, str(current_user.id)
            ),
            "can_delete": await proposal_service.validation.check_delete_permission(
                proposal_id, str(current_user.id)
            ),
            "can_submit": await proposal_service.validation.check_submit_permission(
                proposal_id, str(current_user.id)
            ),
            "can_approve": await proposal_service.validation.check_approve_permission(
                str(current_user.id)
            ),
            "is_creator": await proposal_service.validation.check_creator_permission(
                str(current_user.id)
            ),
            "is_admin": await proposal_service.validation.check_admin_permission(
                str(current_user.id)
            )
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "proposal_id": proposal_id,
                    "user_id": str(current_user.id),
                    "permissions": permissions
                },
                "module_info": {
                    "service": "ProposalValidationService",
                    "method": "check_permissions"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檢查權限時發生錯誤: {str(e)}")


@router.post("/{proposal_id}/validate-transition")
async def validate_status_transition(
    proposal_id: str,
    target_status: ProposalStatus = Body(..., description="目標狀態"),
    current_user = Depends(get_current_user)
):
    """
    驗證狀態轉換 - 模組化版本
    
    - **需要權限**: 已登入用戶
    - **功能**: 驗證是否可以進行指定的狀態轉換
    - **模組**: ProposalValidationService.validate_status_transition()
    """
    try:
        # 先取得當前提案狀態
        proposal = await proposal_service.get_proposal_by_id(
            proposal_id, str(current_user.id)
        )
        
        if not proposal:
            raise HTTPException(status_code=404, detail="提案不存在或無權限查看")
        
        is_valid = await proposal_service.validation.validate_status_transition(
            proposal.status, target_status
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "proposal_id": proposal_id,
                    "current_status": proposal.status,
                    "target_status": target_status,
                    "is_valid_transition": is_valid,
                    "message": "狀態轉換有效" if is_valid else "狀態轉換無效"
                },
                "module_info": {
                    "service": "ProposalValidationService",
                    "method": "validate_status_transition"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"驗證狀態轉換時發生錯誤: {str(e)}")


# ==================== 統計和監控端點 ====================

@router.get("/analytics/summary")
async def get_proposal_summary():
    """
    取得提案總覽 - 模組化版本
    
    - **權限**: 公開端點
    - **功能**: 取得提案系統的基本統計資訊
    - **模組**: 多個服務模組組合
    """
    try:
        # 組合多個服務的統計資訊
        search_stats = await proposal_service.search.get_search_statistics()
        
        # 基本統計
        basic_stats = {
            "total_proposals": search_stats.get("total_proposals", 0),
            "active_proposals": search_stats.get("active_proposals", 0),
            "pending_reviews": search_stats.get("pending_reviews", 0)
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "summary": basic_stats,
                    "search_statistics": search_stats,
                    "system_status": "operational",
                    "last_updated": datetime.now().isoformat()
                },
                "module_info": {
                    "services": ["ProposalSearchService", "統計組合"],
                    "method": "get_proposal_summary"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得提案總覽時發生錯誤: {str(e)}")


@router.get("/health/modules")
async def check_modules_health():
    """
    檢查所有模組健康狀態
    
    - **權限**: 公開端點
    - **功能**: 檢查各個服務模組的健康狀態
    - **模組**: 所有服務模組
    """
    try:
        health_status = {
            "overall_status": "healthy",
            "modules": {
                "validation_service": {
                    "status": "healthy" if hasattr(proposal_service, 'validation') else "error",
                    "loaded": hasattr(proposal_service, 'validation'),
                    "dependencies": ["None"]
                },
                "core_service": {
                    "status": "healthy" if hasattr(proposal_service, 'core') else "error",
                    "loaded": hasattr(proposal_service, 'core'),
                    "dependencies": ["validation_service"]
                },
                "workflow_service": {
                    "status": "healthy" if hasattr(proposal_service, 'workflow') else "error",
                    "loaded": hasattr(proposal_service, 'workflow'),
                    "dependencies": ["core_service", "validation_service"]
                },
                "search_service": {
                    "status": "healthy" if hasattr(proposal_service, 'search') else "error",
                    "loaded": hasattr(proposal_service, 'search'),
                    "dependencies": ["None"]
                },
                "admin_service": {
                    "status": "healthy" if hasattr(proposal_service, 'admin') else "error",
                    "loaded": hasattr(proposal_service, 'admin'),
                    "dependencies": ["core_service", "workflow_service", "validation_service"]
                }
            },
            "timestamp": datetime.now().isoformat(),
            "architecture_version": "2.0.0"
        }
        
        # 檢查是否所有模組都正常
        all_healthy = all(
            module["status"] == "healthy" 
            for module in health_status["modules"].values()
        )
        
        health_status["overall_status"] = "healthy" if all_healthy else "degraded"
        
        return JSONResponse(
            status_code=200 if all_healthy else 503,
            content={
                "success": all_healthy,
                "data": health_status,
                "message": "所有模組正常運行" if all_healthy else "部分模組異常"
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": f"健康檢查失敗: {str(e)}",
                "error": str(e)
            }
        ), detail=f"創建提案時發生錯誤: {str(e)}")


@router.get("/{proposal_id}", response_model=Dict[str, Any])
async def get_proposal(
    proposal_id: str,
    increment_view: bool = Query(False, description="是否增加瀏覽量"),
    current_user = Depends(get_current_user_optional)
):
    """
    取得提案詳情 - 模組化版本
    
    - **權限**: 公開提案無需登入，私有內容需要權限
    - **功能**: 根據用戶權限返回相應層級的提案資訊
    - **模組**: ProposalCoreService.get_proposal_by_id()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        
        proposal = await proposal_service.get_proposal_by_id(
            proposal_id=proposal_id,
            user_id=user_id,
            increment_view=increment_view
        )
        
        if not proposal:
            raise HTTPException(status_code=404, detail="提案不存在或無權限查看")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "proposal_id": str(proposal.id),
                    "company_info": proposal.company_info.dict() if proposal.company_info else None,
                    "financial_info": proposal.financial_info.dict() if proposal.financial_info else None,
                    "business_model": proposal.business_model.dict() if proposal.business_model else None,
                    "teaser_content": proposal.teaser_content.dict() if proposal.teaser_content else None,
                    "status": proposal.status,
                    "view_count": proposal.view_count,
                    "created_at": proposal.created_at.isoformat(),
                    "updated_at": proposal.updated_at.isoformat()
                },
                "module_info": {
                    "service": "ProposalCoreService",
                    "method": "get_proposal_by_id",
                    "increment_view": increment_view
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得提案時發生錯誤: {str(e)}")


@router.put("/{proposal_id}", response_model=Dict[str, Any])
async def update_proposal(
    proposal_id: str,
    update_data: ProposalUpdate,
    current_user = Depends(get_current_user)
):
    """
    更新提案 - 模組化版本
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 更新提案資訊，記錄修改歷史
    - **模組**: ProposalCoreService.update_proposal()
    """
    try:
        success = await proposal_service.update_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            update_data=update_data
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="更新提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案更新成功",
                "module_info": {
                    "service": "ProposalCoreService",
                    "method": "update_proposal"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新提案時發生錯誤: {str(e)}")


@router.delete("/{proposal_id}", response_model=Dict[str, Any])
async def delete_proposal(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    刪除提案 - 模組化版本
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 軟刪除提案，保留歷史記錄
    - **模組**: ProposalCoreService.delete_proposal()
    """
    try:
        success = await proposal_service.delete_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id)
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="刪除提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案刪除成功",
                "module_info": {
                    "service": "ProposalCoreService",
                    "method": "delete_proposal"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除提案時發生錯誤: {str(e)}")


@router.get("/creator/{creator_id}", response_model=Dict[str, Any])
async def get_proposals_by_creator(
    creator_id: str,
    status_filter: Optional[List[ProposalStatus]] = Query(None, description="狀態篩選"),
    current_user = Depends(get_current_user)
):
    """
    取得創建者的提案列表 - 模組化版本
    
    - **需要權限**: 創建者本人或管理員
    - **功能**: 取得指定創建者的所有提案
    - **模組**: ProposalCoreService.get_proposals_by_creator()
    """
    try:
        proposals = await proposal_service.get_proposals_by_creator(
            creator_id=creator_id,
            status_filter=status_filter
        )
        
        proposals_data = []
        for proposal in proposals:
            proposals_data.append({
                "proposal_id": str(proposal.id),
                "company_name": proposal.company_info.company_name if proposal.company_info else "未填寫",
                "status": proposal.status,
                "view_count": proposal.view_count,
                "created_at": proposal.created_at.isoformat(),
                "updated_at": proposal.updated_at.isoformat()
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "proposals": proposals_data,
                    "total_count": len(proposals_data),
                    "creator_id": creator_id,
                    "status_filter": status_filter
                },
                "module_info": {
                    "service": "ProposalCoreService",
                    "method": "get_proposals_by_creator"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得提案列表時發生錯誤: {str(e)}")


# ==================== 工作流程管理端點 ====================

@router.post("/{proposal_id}/submit")
async def submit_proposal(
    proposal_id: str,
    submit_data: Optional[ProposalSubmitRequest] = Body(None),
    current_user = Depends(get_current_user)
):
    """
    提交提案審核 - 模組化版本
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 將草稿狀態的提案提交給管理員審核
    - **模組**: ProposalWorkflowService.submit_proposal()
    """
    try:
        success = await proposal_service.submit_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            submit_data=submit_data
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="提交提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案已提交審核",
                "module_info": {
                    "service": "ProposalWorkflowService",
                    "method": "submit_proposal",
                    "workflow": "draft → under_review"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交提案時發生錯誤: {str(e)}")


@router.post("/{proposal_id}/withdraw")
async def withdraw_proposal(
    proposal_id: str,
    reason: Optional[str] = Body(None, description="撤回原因"),
    current_user = Depends(get_current_user)
):
    """
    撤回提案 - 模組化版本
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 從審核中撤回提案，回到草稿狀態
    - **模組**: ProposalWorkflowService.withdraw_proposal()
    """
    try:
        success = await proposal_service.withdraw_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            reason=reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="撤回提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案已撤回",
                "module_info": {
                    "service": "ProposalWorkflowService",
                    "method": "withdraw_proposal",
                    "workflow": "under_review → draft"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撤回提案時發生錯誤: {str(e)}")


@router.get("/{proposal_id}/workflow-history")
async def get_workflow_history(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    取得工作流程歷史 - 模組化版本
    
    - **需要權限**: 已登入用戶
    - **功能**: 查看提案的狀態變更歷史
    - **模組**: ProposalWorkflowService.get_workflow_history()
    """
    try:
        history = await proposal_service.workflow.get_workflow_history(proposal_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": history,
                "module_info": {
                    "service": "ProposalWorkflowService",
                    "method": "get_workflow_history"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得工作流程歷史時發生錯誤: {str(e)}")


# ==================== 搜尋和篩選端點 ====================

@router.get("/search/", response_model=Dict[str, Any])
async def search_proposals(
    q: Optional[str] = Query(None, description="搜尋關鍵字"),
    industry: Optional[Industry] = Query(None, description="產業篩選"),
    company_size: Optional[CompanySize] = Query(None, description="公司規模篩選"),
    status: Optional[ProposalStatus] = Query(None, description="狀態篩選"),
    location: Optional[str] = Query(None, description="地區篩選"),
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=100, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    智能搜尋提案 - 模組化版本
    
    - **權限**: 公開搜尋，登入用戶可看更多內容
    - **功能**: 支援關鍵字搜尋和多維度篩選
    - **模組**: ProposalSearchService.search_proposals()
    """
    try:
        search_params = ProposalSearchParams(
            query=q,
            industry=industry,
            company_size=company_size,
            status=status,
            location=location,
            page=page,
            limit=limit
        )
        
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.search_proposals(search_params, user_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "search_params": {
                    "query": q,
                    "industry": industry,
                    "company_size": company_size,
                    "status": status,
                    "location": location,
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "service": "ProposalSearchService",
                    "method": "search_proposals"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋提案時發生錯誤: {str(e)}")


@router.get("/search/full-text")
async def full_text_search(
    q: str = Query(..., description="全文搜尋關鍵字"),
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    全文搜尋 - 模組化版本
    
    - **權限**: 公開搜尋
    - **功能**: 在提案內容中進行全文搜尋
    - **模組**: ProposalSearchService.full_text_search()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.full_text_search(q, page, limit, user_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "search_query": q,
                "module_info": {
                    "service": "ProposalSearchService",
                    "method": "full_text_search"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"全文搜尋時發生錯誤: {str(e)}")


@router.get("/search/statistics")
async def get_search_statistics():
    """
    取得搜尋統計 - 模組化版本
    
    - **權限**: 公開端點
    - **功能**: 提供搜尋相關的統計資訊
    - **模組**: ProposalSearchService.get_search_statistics()
    """
    try:
        stats = await proposal_service.search.get_search_statistics()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": stats,
                "module_info": {
                    "service": "ProposalSearchService",
                    "method": "get_search_statistics"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得搜尋統計時發生錯誤: {str(e)}")


# ==================== 管理員功能端點 ====================

@router.post("/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    approve_data: ProposalApproveRequest,
    current_user = Depends(require_admin)
):
    """
    審核通過提案 - 模組化版本
    
    - **需要權限**: 管理員
    - **功能**: 審核通過提案，更新狀態並記錄
    - **模組**: ProposalAdminService.approve_proposal()
    """
    try:
        success = await proposal_service.admin.approve_proposal(
            proposal_id=proposal_id,
            admin_id=str(current_user.id),
            approve_data=approve_data
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="審核通過失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案審核通過",
                "module_info": {
                    "service": "ProposalAdminService",
                    "method": "approve_proposal",
                    "workflow": "under_review → approved"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"審核提案時發生錯誤: {str(e)}")


@router.post("/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    reject_data: ProposalRejectRequest,
    current_user = Depends(require_admin)
):
    """
    審核拒絕提案 - 模組化版本
    
    - **需要權限**: 管理員
    - **功能**: 審核拒絕提案，要求修改
    - **模組**: ProposalAdminService.reject_proposal()
    """
    try:
        success = await proposal_service.admin.reject_proposal(
            proposal_id=proposal_id,
            admin_id=str(current_user.id),
            reject_data=reject_data
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="審核拒絕失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案審核拒絕",
                "module_info": {
                    "service": "ProposalAdminService",
                    "method": "reject_proposal",
                    "workflow": "under_review → rejected"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"拒絕提案時發生錯誤: {str(e)}")


@router.get("/admin/pending-reviews")
async def get_pending_reviews(
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
    current_user = Depends(require_admin)
):
    """
    取得待審核提案列表 - 模組化版本
    
    - **需要權限**: 管理員
    - **功能**: 取得所有待審核的提案
    - **模組**: ProposalAdminService.get_pending_reviews()
    """
    try:
        pending_reviews = await proposal_service.admin.get_pending_reviews(page, limit)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": pending_reviews,
                "module_info": {
                    "service": "ProposalAdminService",
                    "method": "get_pending_reviews"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得待審核列表時發生錯誤: {str(e)}")


@router.post("/admin/batch-approve")
async def batch_approve_proposals(
    proposal_ids: List[str] = Body(..., description="提案 ID 列表"),
    comment: Optional[str] = Body(None, description="批量審核備註"),
    current_user = Depends(require_admin)
):
    """
    批量審核通過 - 模組化版本
    
    - **需要權限**: 管理員
    - **功能**: 批量審核通過多個提案
    - **模組**: ProposalAdminService.batch_approve()
    """
    try:
        results = await proposal_service.admin.batch_approve(
            proposal_ids=proposal_ids,
            admin_id=str(current_user.id),
            comment=comment
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"批量審核完成，成功: {results['success_count']}，失敗: {results['failed_count']}",
                "data": results,
                "module_info": {
                    "service": "ProposalAdminService",
                    "method": "batch_approve"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500