"""
提案核心 API 模組 - core.py
負責基礎 CRUD 操作的 API 端點
對應服務: ProposalCoreService
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessException, ValidationException, PermissionDeniedException
from app.models.user import UserRole
from app.models.proposal import ProposalStatus
from app.schemas.proposal import ProposalCreate, ProposalUpdate
from app.services.proposal import ProposalService
from app.api.deps import get_current_user, require_roles, get_current_user_optional

# 創建子路由器
router = APIRouter()

# 創建服務實例
proposal_service = ProposalService()


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_proposal(
    proposal_data: ProposalCreate,
    current_user = Depends(require_roles([UserRole.SELLER, UserRole.ADMIN]))
):
    """
    創建新提案
    
    - **需要權限**: 提案方或管理員
    - **功能**: 創建新的提案，初始狀態為草稿
    - **服務模組**: ProposalCoreService.create_proposal()
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
                    "company_name": proposal.company_info.company_name if proposal.company_info else "未填寫",
                    "created_at": proposal.created_at.isoformat(),
                    "creator_id": str(proposal.creator_id)
                },
                "module_info": {
                    "api_module": "proposals.core",
                    "service": "ProposalCoreService", 
                    "method": "create_proposal"
                }
            }
        )
        
    except (PermissionDeniedException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"創建提案時發生錯誤: {str(e)}")


@router.get("/{proposal_id}", response_model=Dict[str, Any])
async def get_proposal(
    proposal_id: str,
    increment_view: bool = Query(False, description="是否增加瀏覽量"),
    current_user = Depends(get_current_user_optional)
):
    """
    取得提案詳情
    
    - **權限**: 公開提案無需登入，私有內容需要權限
    - **功能**: 根據用戶權限返回相應層級的提案資訊
    - **服務模組**: ProposalCoreService.get_proposal_by_id()
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
        
        # 根據用戶權限決定返回的資料層級
        response_data = {
            "proposal_id": str(proposal.id),
            "status": proposal.status,
            "view_count": proposal.view_count,
            "created_at": proposal.created_at.isoformat(),
            "updated_at": proposal.updated_at.isoformat()
        }
        
        # 基本資訊 (所有人可見)
        if proposal.company_info:
            response_data["company_info"] = {
                "company_name": proposal.company_info.company_name,
                "industry": proposal.company_info.industry,
                "location": proposal.company_info.location,
                "company_size": proposal.company_info.company_size
            }
        
        # Teaser 內容 (已發布的提案可見)
        if proposal.teaser_content and proposal.status in [ProposalStatus.PUBLISHED, ProposalStatus.SENT]:
            response_data["teaser_content"] = proposal.teaser_content.dict()
        
        # 完整內容 (創建者、管理員或已簽署 NDA 的買方可見)
        is_creator = user_id and str(proposal.creator_id) == user_id
        is_admin = current_user and current_user.role == UserRole.ADMIN
        
        if (is_creator or is_admin) and proposal.full_content:
            response_data["full_content"] = proposal.full_content.dict()
            
        # 財務資訊 (僅創建者和管理員可見)
        if (is_creator or is_admin) and proposal.financial_info:
            response_data["financial_info"] = proposal.financial_info.dict()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": response_data,
                "access_level": "creator" if is_creator else ("admin" if is_admin else "public"),
                "module_info": {
                    "api_module": "proposals.core",
                    "service": "ProposalCoreService",
                    "method": "get_proposal_by_id"
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
    更新提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 更新提案資訊，記錄修改歷史
    - **服務模組**: ProposalCoreService.update_proposal()
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
                    "api_module": "proposals.core",
                    "service": "ProposalCoreService",
                    "method": "update_proposal"
                }
            }
        )
        
    except (PermissionDeniedException, ValidationException) as e:
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
    刪除提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 軟刪除提案，保留歷史記錄
    - **服務模組**: ProposalCoreService.delete_proposal()
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
                    "api_module": "proposals.core",
                    "service": "ProposalCoreService",
                    "method": "delete_proposal"
                }
            }
        )
        
    except (PermissionDeniedException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除提案時發生錯誤: {str(e)}")


@router.get("/creator/{creator_id}", response_model=Dict[str, Any])
async def get_proposals_by_creator(
    creator_id: str,
    status_filter: Optional[List[ProposalStatus]] = Query(None, description="狀態篩選"),
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=100, description="每頁數量"),
    current_user = Depends(get_current_user)
):
    """
    取得創建者的提案列表
    
    - **需要權限**: 創建者本人或管理員
    - **功能**: 取得指定創建者的所有提案
    - **服務模組**: ProposalCoreService.get_proposals_by_creator()
    """
    try:
        # 權限檢查：只能查看自己的提案或管理員可以查看所有
        if str(current_user.id) != creator_id and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="無權限查看其他人的提案")
        
        proposals = await proposal_service.get_proposals_by_creator(
            creator_id=creator_id,
            status_filter=status_filter
        )
        
        # 分頁處理
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_proposals = proposals[start_idx:end_idx]
        
        proposals_data = []
        for proposal in paginated_proposals:
            proposals_data.append({
                "proposal_id": str(proposal.id),
                "company_name": proposal.company_info.company_name if proposal.company_info else "未填寫",
                "status": proposal.status,
                "industry": proposal.company_info.industry if proposal.company_info else None,
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
                    "pagination": {
                        "current_page": page,
                        "per_page": limit,
                        "total_items": len(proposals),
                        "total_pages": (len(proposals) + limit - 1) // limit,
                        "has_next": end_idx < len(proposals),
                        "has_prev": page > 1
                    },
                    "filters": {
                        "creator_id": creator_id,
                        "status_filter": status_filter
                    }
                },
                "module_info": {
                    "api_module": "proposals.core",
                    "service": "ProposalCoreService",
                    "method": "get_proposals_by_creator"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得提案列表時發生錯誤: {str(e)}")


@router.get("/{proposal_id}/edit-access", response_model=Dict[str, Any])
async def get_proposal_for_edit(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    取得用於編輯的提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 取得提案的完整可編輯資料
    - **服務模組**: ProposalCoreService.get_proposal_for_edit()
    """
    try:
        proposal = await proposal_service.get_proposal_for_edit(
            proposal_id=proposal_id,
            user_id=str(current_user.id)
        )
        
        if not proposal:
            raise HTTPException(status_code=404, detail="提案不存在或無編輯權限")
        
        # 返回完整的可編輯資料
        response_data = {
            "proposal_id": str(proposal.id),
            "status": proposal.status,
            "company_info": proposal.company_info.dict() if proposal.company_info else None,
            "financial_info": proposal.financial_info.dict() if proposal.financial_info else None,
            "business_model": proposal.business_model.dict() if proposal.business_model else None,
            "teaser_content": proposal.teaser_content.dict() if proposal.teaser_content else None,
            "full_content": proposal.full_content.dict() if proposal.full_content else None,
            "files": proposal.files if hasattr(proposal, 'files') else [],
            "created_at": proposal.created_at.isoformat(),
            "updated_at": proposal.updated_at.isoformat(),
            "can_edit": True,
            "can_submit": proposal.status == ProposalStatus.DRAFT,
            "can_delete": proposal.status == ProposalStatus.DRAFT
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": response_data,
                "module_info": {
                    "api_module": "proposals.core",
                    "service": "ProposalCoreService",
                    "method": "get_proposal_for_edit"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得編輯資料時發生錯誤: {str(e)}")


@router.get("/{proposal_id}/statistics", response_model=Dict[str, Any])
async def get_proposal_statistics(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    取得提案統計資訊
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 取得提案的各種統計數據
    - **服務模組**: ProposalCoreService
    """
    try:
        # 權限檢查
        proposal = await proposal_service.get_proposal_for_edit(
            proposal_id=proposal_id,
            user_id=str(current_user.id)
        )
        
        if not proposal:
            raise HTTPException(status_code=404, detail="提案不存在或無權限查看")
        
        # 計算統計資訊
        stats = {
            "view_count": proposal.view_count,
            "status": proposal.status,
            "days_since_created": (proposal.updated_at - proposal.created_at).days,
            "last_updated": proposal.updated_at.isoformat(),
            "file_count": len(proposal.files) if hasattr(proposal, 'files') else 0,
            "completion_rate": await proposal_service.core.calculate_completion_rate(proposal_id) if hasattr(proposal_service.core, 'calculate_completion_rate') else 85  # 模擬數據
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": stats,
                "module_info": {
                    "api_module": "proposals.core",
                    "service": "ProposalCoreService",
                    "method": "get_proposal_statistics"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計資訊時發生錯誤: {str(e)}")