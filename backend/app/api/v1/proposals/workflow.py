"""
提案工作流程 API 模組 - workflow.py
負責提案狀態流轉管理的 API 端點
對應服務: ProposalWorkflowService
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body, status
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessException, ValidationException, PermissionDeniedException
from app.models.proposal import ProposalStatus
from app.schemas.proposal import ProposalSubmitRequest
from app.services.proposal import ProposalService
from app.api.deps import get_current_user

# 創建子路由器
router = APIRouter()

# 創建服務實例
proposal_service = ProposalService()


@router.post("/{proposal_id}/submit", response_model=Dict[str, Any])
async def submit_proposal(
    proposal_id: str,
    submit_data: Optional[ProposalSubmitRequest] = Body(None),
    current_user = Depends(get_current_user)
):
    """
    提交提案審核
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 將草稿狀態的提案提交給管理員審核
    - **服務模組**: ProposalWorkflowService.submit_proposal()
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
                "workflow_info": {
                    "from_status": "draft",
                    "to_status": "under_review",
                    "submitted_by": str(current_user.id),
                    "submitted_at": "now"
                },
                "module_info": {
                    "api_module": "proposals.workflow",
                    "service": "ProposalWorkflowService",
                    "method": "submit_proposal"
                }
            }
        )
        
    except (PermissionDeniedException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交提案時發生錯誤: {str(e)}")


@router.post("/{proposal_id}/withdraw", response_model=Dict[str, Any])
async def withdraw_proposal(
    proposal_id: str,
    reason: Optional[str] = Body(None, description="撤回原因"),
    current_user = Depends(get_current_user)
):
    """
    撤回提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 從審核中撤回提案，回到草稿狀態
    - **服務模組**: ProposalWorkflowService.withdraw_proposal()
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
                "workflow_info": {
                    "from_status": "under_review",
                    "to_status": "draft",
                    "withdrawn_by": str(current_user.id),
                    "reason": reason
                },
                "module_info": {
                    "api_module": "proposals.workflow",
                    "service": "ProposalWorkflowService",
                    "method": "withdraw_proposal"
                }
            }
        )
        
    except (PermissionDeniedException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撤回提案時發生錯誤: {str(e)}")


@router.post("/{proposal_id}/publish", response_model=Dict[str, Any])
async def publish_proposal(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    發布提案
    
    - **需要權限**: 管理員審核通過後自動發布，或創建者手動發布
    - **功能**: 將審核通過的提案發布到平台
    - **服務模組**: ProposalWorkflowService.publish_proposal()
    """
    try:
        success = await proposal_service.workflow.publish_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id)
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="發布提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案已發布",
                "workflow_info": {
                    "from_status": "approved",
                    "to_status": "published",
                    "published_by": str(current_user.id)
                },
                "module_info": {
                    "api_module": "proposals.workflow",
                    "service": "ProposalWorkflowService",
                    "method": "publish_proposal"
                }
            }
        )
        
    except (PermissionDeniedException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"發布提案時發生錯誤: {str(e)}")


@router.post("/{proposal_id}/archive", response_model=Dict[str, Any])
async def archive_proposal(
    proposal_id: str,
    reason: Optional[str] = Body(None, description="歸檔原因"),
    current_user = Depends(get_current_user)
):
    """
    歸檔提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 將提案歸檔，停止展示但保留記錄
    - **服務模組**: ProposalWorkflowService.archive_proposal()
    """
    try:
        success = await proposal_service.workflow.archive_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            reason=reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="歸檔提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案已歸檔",
                "workflow_info": {
                    "to_status": "archived",
                    "archived_by": str(current_user.id),
                    "reason": reason
                },
                "module_info": {
                    "api_module": "proposals.workflow",
                    "service": "ProposalWorkflowService",
                    "method": "archive_proposal"
                }
            }
        )
        
    except (PermissionDeniedException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"歸檔提案時發生錯誤: {str(e)}")


@router.get("/{proposal_id}/workflow-history", response_model=Dict[str, Any])
async def get_workflow_history(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    取得工作流程歷史
    
    - **需要權限**: 已登入用戶
    - **功能**: 查看提案的狀態變更歷史
    - **服務模組**: ProposalWorkflowService.get_workflow_history()
    """
    try:
        history = await proposal_service.workflow.get_workflow_history(proposal_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "proposal_id": proposal_id,
                    "workflow_history": history,
                    "total_transitions": len(history) if history else 0
                },
                "module_info": {
                    "api_module": "proposals.workflow",
                    "service": "ProposalWorkflowService",
                    "method": "get_workflow_history"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得工作流程歷史時發生錯誤: {str(e)}")


@router.post("/{proposal_id}/validate-transition", response_model=Dict[str, Any])
async def validate_status_transition(
    proposal_id: str,
    target_status: ProposalStatus = Body(..., description="目標狀態"),
    current_user = Depends(get_current_user)
):
    """
    驗證狀態轉換
    
    - **需要權限**: 已登入用戶
    - **功能**: 驗證是否可以進行指定的狀態轉換
    - **服務模組**: ProposalValidationService.validate_status_transition()
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
        
        # 取得可用的狀態轉換
        available_transitions = await proposal_service.workflow.get_available_transitions(
            proposal_id, str(current_user.id)
        ) if hasattr(proposal_service.workflow, 'get_available_transitions') else []
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "proposal_id": proposal_id,
                    "current_status": proposal.status,
                    "target_status": target_status,
                    "is_valid_transition": is_valid,
                    "available_transitions": available_transitions,
                    "message": "狀態轉換有效" if is_valid else "狀態轉換無效"
                },
                "module_info": {
                    "api_module": "proposals.workflow",
                    "service": "ProposalValidationService",
                    "method": "validate_status_transition"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"驗證狀態轉換時發生錯誤: {str(e)}")


@router.get("/{proposal_id}/available-actions", response_model=Dict[str, Any])
async def get_available_actions(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    取得可用操作
    
    - **需要權限**: 已登入用戶
    - **功能**: 根據當前狀態和用戶權限，取得可執行的操作
    - **服務模組**: ProposalWorkflowService
    """
    try:
        # 取得提案
        proposal = await proposal_service.get_proposal_by_id(
            proposal_id, str(current_user.id)
        )
        
        if not proposal:
            raise HTTPException(status_code=404, detail="提案不存在或無權限查看")
        
        # 檢查用戶權限
        is_creator = str(proposal.creator_id) == str(current_user.id)
        is_admin = current_user.role.value == "admin"
        
        available_actions = []
        
        # 根據狀態和權限決定可用操作
        if proposal.status == ProposalStatus.DRAFT and is_creator:
            available_actions.extend([
                {"action": "submit", "description": "提交審核", "method": "POST"},
                {"action": "update", "description": "編輯提案", "method": "PUT"},
                {"action": "delete", "description": "刪除提案", "method": "DELETE"}
            ])
        
        if proposal.status == ProposalStatus.UNDER_REVIEW:
            if is_creator:
                available_actions.append(
                    {"action": "withdraw", "description": "撤回提案", "method": "POST"}
                )
            if is_admin:
                available_actions.extend([
                    {"action": "approve", "description": "審核通過", "method": "POST"},
                    {"action": "reject", "description": "審核拒絕", "method": "POST"}
                ])
        
        if proposal.status == ProposalStatus.APPROVED and (is_creator or is_admin):
            available_actions.append(
                {"action": "publish", "description": "發布提案", "method": "POST"}
            )
        
        if proposal.status in [ProposalStatus.PUBLISHED, ProposalStatus.SENT] and (is_creator or is_admin):
            available_actions.append(
                {"action": "archive", "description": "歸檔提案", "method": "POST"}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "proposal_id": proposal_id,
                    "current_status": proposal.status,
                    "user_role": current_user.role.value,
                    "is_creator": is_creator,
                    "available_actions": available_actions,
                    "total_actions": len(available_actions)
                },
                "module_info": {
                    "api_module": "proposals.workflow",
                    "service": "ProposalWorkflowService",
                    "method": "get_available_actions"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得可用操作時發生錯誤: {str(e)}")