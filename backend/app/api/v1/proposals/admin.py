"""
提案管理員功能 API 模組 - admin.py
負責管理員專用功能的 API 端點
對應服務: ProposalAdminService
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessException, ValidationException, PermissionException
from app.schemas.proposal import ProposalApproveRequest, ProposalRejectRequest
from app.services.proposal import ProposalService
from app.api.deps import get_current_user, require_admin

# 創建子路由器
router = APIRouter()

# 創建服務實例
proposal_service = ProposalService()


@router.post("/{proposal_id}/approve", response_model=Dict[str, Any])
async def approve_proposal(
    proposal_id: str,
    approve_data: ProposalApproveRequest,
    current_user = Depends(require_admin)
):
    """
    審核通過提案
    
    - **需要權限**: 管理員
    - **功能**: 審核通過提案，更新狀態並記錄
    - **服務模組**: ProposalAdminService.approve_proposal()
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
                "approval_info": {
                    "approved_by": str(current_user.id),
                    "approved_at": datetime.now().isoformat(),
                    "comment": approve_data.comment if hasattr(approve_data, 'comment') else None
                },
                "workflow_info": {
                    "from_status": "under_review",
                    "to_status": "approved"
                },
                "module_info": {
                    "api_module": "proposals.admin",
                    "service": "ProposalAdminService",
                    "method": "approve_proposal"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"審核提案時發生錯誤: {str(e)}")


@router.post("/{proposal_id}/reject", response_model=Dict[str, Any])
async def reject_proposal(
    proposal_id: str,
    reject_data: ProposalRejectRequest,
    current_user = Depends(require_admin)
):
    """
    審核拒絕提案
    
    - **需要權限**: 管理員
    - **功能**: 審核拒絕提案，要求修改
    - **服務模組**: ProposalAdminService.reject_proposal()
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
                "rejection_info": {
                    "rejected_by": str(current_user.id),
                    "rejected_at": datetime.now().isoformat(),
                    "reason": reject_data.reason if hasattr(reject_data, 'reason') else "未提供原因",
                    "suggestions": reject_data.suggestions if hasattr(reject_data, 'suggestions') else []
                },
                "workflow_info": {
                    "from_status": "under_review",
                    "to_status": "rejected"
                },
                "module_info": {
                    "api_module": "proposals.admin",
                    "service": "ProposalAdminService",
                    "method": "reject_proposal"
                }
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"拒絕提案時發生錯誤: {str(e)}")


@router.get("/admin/pending-reviews", response_model=Dict[str, Any])
async def get_pending_reviews(
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
    priority: Optional[str] = Query(None, description="優先級篩選 (high/medium/low)"),
    current_user = Depends(require_admin)
):
    """
    取得待審核提案列表
    
    - **需要權限**: 管理員
    - **功能**: 取得所有待審核的提案
    - **服務模組**: ProposalAdminService.get_pending_reviews()
    """
    try:
        pending_reviews = await proposal_service.admin.get_pending_reviews(
            page=page, 
            limit=limit,
            priority=priority
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": pending_reviews,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "priority_filter": priority
                },
                "module_info": {
                    "api_module": "proposals.admin",
                    "service": "ProposalAdminService",
                    "method": "get_pending_reviews"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得待審核列表時發生錯誤: {str(e)}")


@router.post("/admin/batch-approve", response_model=Dict[str, Any])
async def batch_approve_proposals(
    proposal_ids: List[str] = Body(..., description="提案 ID 列表"),
    comment: Optional[str] = Body(None, description="批量審核備註"),
    current_user = Depends(require_admin)
):
    """
    批量審核通過
    
    - **需要權限**: 管理員
    - **功能**: 批量審核通過多個提案
    - **服務模組**: ProposalAdminService.batch_approve()
    """
    try:
        if len(proposal_ids) > 50:  # 限制批量操作數量
            raise HTTPException(status_code=400, detail="批量操作數量不能超過 50 個")
        
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
                "data": {
                    "total_requested": len(proposal_ids),
                    "success_count": results['success_count'],
                    "failed_count": results['failed_count'],
                    "success_ids": results.get('success_ids', []),
                    "failed_items": results.get('failed_items', []),
                    "batch_comment": comment,
                    "processed_by": str(current_user.id),
                    "processed_at": datetime.now().isoformat()
                },
                "module_info": {
                    "api_module": "proposals.admin",
                    "service": "ProposalAdminService",
                    "method": "batch_approve"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量審核時發生錯誤: {str(e)}")


@router.post("/admin/batch-reject", response_model=Dict[str, Any])
async def batch_reject_proposals(
    proposal_ids: List[str] = Body(..., description="提案 ID 列表"),
    reason: str = Body(..., description="批量拒絕原因"),
    current_user = Depends(require_admin)
):
    """
    批量審核拒絕
    
    - **需要權限**: 管理員
    - **功能**: 批量審核拒絕多個提案
    - **服務模組**: ProposalAdminService.batch_reject()
    """
    try:
        if len(proposal_ids) > 50:  # 限制批量操作數量
            raise HTTPException(status_code=400, detail="批量操作數量不能超過 50 個")
        
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
                "data": {
                    "total_requested": len(proposal_ids),
                    "success_count": results['success_count'],
                    "failed_count": results['failed_count'],
                    "success_ids": results.get('success_ids', []),
                    "failed_items": results.get('failed_items', []),
                    "batch_reason": reason,
                    "processed_by": str(current_user.id),
                    "processed_at": datetime.now().isoformat()
                },
                "module_info": {
                    "api_module": "proposals.admin",
                    "service": "ProposalAdminService",
                    "method": "batch_reject"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量拒絕時發生錯誤: {str(e)}")


@router.get("/admin/statistics", response_model=Dict[str, Any])
async def get_proposal_statistics(
    start_date: Optional[datetime] = Query(None, description="開始日期"),
    end_date: Optional[datetime] = Query(None, description="結束日期"),
    granularity: str = Query("day", description="統計粒度 (day/week/month)"),
    current_user = Depends(require_admin)
):
    """
    取得提案統計
    
    - **需要權限**: 管理員
    - **功能**: 取得提案的各種統計資訊
    - **服務模組**: ProposalAdminService.get_proposal_statistics()
    """
    try:
        stats = await proposal_service.admin.get_proposal_statistics(
            start_date=start_date, 
            end_date=end_date,
            granularity=granularity
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": stats,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "granularity": granularity
                },
                "module_info": {
                    "api_module": "proposals.admin",
                    "service": "ProposalAdminService",
                    "method": "get_proposal_statistics"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計資訊時發生錯誤: {str(e)}")


@router.get("/admin/dashboard", response_model=Dict[str, Any])
async def get_admin_dashboard(
    current_user = Depends(require_admin)
):
    """
    管理員儀表板
    
    - **需要權限**: 管理員
    - **功能**: 取得管理員儀表板的完整資訊
    - **服務模組**: ProposalAdminService.get_admin_dashboard()
    """
    try:
        dashboard_data = await proposal_service.admin.get_admin_dashboard()
        
        # 補充當前管理員的個人統計
        admin_stats = {
            "admin_id": str(current_user.id),
            "admin_name": f"{current_user.first_name} {current_user.last_name}",
            "login_time": datetime.now().isoformat(),
            "recent_actions": await proposal_service.admin.get_admin_recent_actions(
                str(current_user.id)
            ) if hasattr(proposal_service.admin, 'get_admin_recent_actions') else []
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    **dashboard_data,
                    "current_admin": admin_stats
                },
                "module_info": {
                    "api_module": "proposals.admin",
                    "service": "ProposalAdminService",
                    "method": "get_admin_dashboard"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得管理員儀表板時發生錯誤: {str(e)}")


@router.get("/admin/audit-log", response_model=Dict[str, Any])
async def get_audit_log(
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(50, ge=1, le=200, description="每頁數量"),
    action_type: Optional[str] = Query(None, description="操作類型篩選"),
    admin_id: Optional[str] = Query(None, description="管理員 ID 篩選"),
    start_date: Optional[datetime] = Query(None, description="開始日期"),
    end_date: Optional[datetime] = Query(None, description="結束日期"),
    current_user = Depends(require_admin)
):
    """
    取得審計日誌
    
    - **需要權限**: 管理員
    - **功能**: 取得管理員操作的審計記錄
    - **服務模組**: ProposalAdminService.get_audit_log()
    """
    try:
        audit_log = await proposal_service.admin.get_audit_log(
            page=page,
            limit=limit,
            action_type=action_type,
            admin_id=admin_id,
            start_date=start_date,
            end_date=end_date
        ) if hasattr(proposal_service.admin, 'get_audit_log') else {
            "logs": [],
            "total_count": 0,
            "message": "審計日誌功能開發中"
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": audit_log,
                "filters": {
                    "action_type": action_type,
                    "admin_id": admin_id,
                    "date_range": {
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None
                    }
                },
                "pagination": {
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "api_module": "proposals.admin",
                    "service": "ProposalAdminService",
                    "method": "get_audit_log"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得審計日誌時發生錯誤: {str(e)}")