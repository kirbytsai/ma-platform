"""
提案管理 API 端點
整合模組化的提案服務，提供完整的 REST API
支援提案 CRUD、工作流程、搜尋、管理員功能
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessException, PermissionException, ValidationException
from app.models.user import UserRole
from app.models.proposal import ProposalStatus, Industry, CompanySize
from app.schemas.proposal import (
    ProposalCreate, ProposalUpdate, ProposalResponse, 
    ProposalSearchParams, ProposalSubmitRequest,
    ProposalApproveRequest, ProposalRejectRequest,
    ProposalListResponse, ProposalStatistics
)
from app.services.proposal import ProposalService
from app.api.deps import (
    get_current_user, require_roles, require_admin,
    PaginationParams, get_current_user_optional
)

router = APIRouter()

# 創建提案服務實例
proposal_service = ProposalService()


# ==================== 基礎 CRUD 端點 ====================

@router.post("/", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_proposal(
    proposal_data: ProposalCreate,
    current_user = Depends(require_roles([UserRole.SELLER, UserRole.ADMIN]))
):
    """
    創建新提案
    
    - **需要權限**: 提案方或管理員
    - **功能**: 創建新的提案，初始狀態為草稿
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
                "data": await proposal_service.get_proposal_public_info(proposal)
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: str,
    current_user = Depends(get_current_user_optional)
):
    """
    取得提案詳情
    
    - **權限**: 公開提案無需登入，私有內容需要權限
    - **功能**: 根據用戶權限返回相應層級的提案資訊
    """
    try:
        user_id = str(current_user.id) if current_user else None
        
        proposal = await proposal_service.get_proposal_by_id(
            proposal_id=proposal_id,
            user_id=user_id,
            increment_view=True
        )
        
        if not proposal:
            raise HTTPException(status_code=404, detail="提案不存在")
        
        # 根據用戶權限決定返回的資料層級
        if current_user:
            permissions = await proposal_service.validation.check_view_permission(
                proposal, user_id
            )
            
            if permissions["can_view_full"]:
                proposal_data = await proposal_service.get_proposal_full_info(proposal)
            elif permissions["can_view_teaser"]:
                proposal_data = await proposal_service.get_proposal_public_info(proposal)
            else:
                raise HTTPException(status_code=403, detail="無權限查看此提案")
        else:
            # 匿名用戶只能看公開提案的基本資訊
            if proposal.status != ProposalStatus.AVAILABLE:
                raise HTTPException(status_code=404, detail="提案不存在")
            proposal_data = await proposal_service.get_proposal_public_info(proposal)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": proposal_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得提案時發生錯誤: {str(e)}")


@router.put("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: str,
    update_data: ProposalUpdate,
    current_user = Depends(get_current_user)
):
    """
    更新提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 更新提案資訊（僅草稿和被拒絕狀態可編輯）
    """
    try:
        success = await proposal_service.update_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            update_data=update_data
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="更新提案失敗")
        
        # 返回更新後的提案
        proposal = await proposal_service.get_proposal_by_id(proposal_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案更新成功",
                "data": await proposal_service.get_proposal_full_info(proposal)
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{proposal_id}")
async def delete_proposal(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    刪除提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 軟刪除提案（歸檔狀態）
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
                "message": "提案刪除成功"
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 搜尋和列表端點 ====================

@router.get("/", response_model=ProposalListResponse)
async def search_proposals(
    keywords: Optional[str] = Query(None, description="搜尋關鍵字"),
    industries: Optional[List[Industry]] = Query(None, description="行業篩選"),
    company_sizes: Optional[List[CompanySize]] = Query(None, description="公司規模篩選"),
    locations: Optional[List[str]] = Query(None, description="地點篩選"),
    min_revenue: Optional[float] = Query(None, description="最小營收"),
    max_revenue: Optional[float] = Query(None, description="最大營收"),
    min_established_year: Optional[int] = Query(None, description="最早成立年份"),
    max_established_year: Optional[int] = Query(None, description="最晚成立年份"),
    sort_by: Optional[str] = Query("created_at", description="排序欄位"),
    sort_order: Optional[str] = Query("desc", description="排序順序"),
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=100, description="每頁大小"),
    current_user = Depends(get_current_user_optional)
):
    """
    搜尋提案
    
    - **權限**: 公開端點，登入用戶可看到更多結果
    - **功能**: 支援關鍵字搜尋、多維度篩選、排序、分頁
    """
    try:
        user_id = str(current_user.id) if current_user else None
        
        # 建構搜尋參數
        search_params = ProposalSearchParams(
            keywords=keywords,
            industries=industries or [],
            company_sizes=company_sizes or [],
            locations=locations or [],
            min_revenue=min_revenue,
            max_revenue=max_revenue,
            min_established_year=min_established_year,
            max_established_year=max_established_year,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        # 執行搜尋
        results = await proposal_service.search_proposals(search_params, user_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋提案時發生錯誤: {str(e)}")


@router.get("/full-text-search/", response_model=List[Dict[str, Any]])
async def full_text_search(
    q: str = Query(..., description="搜尋查詢"),
    limit: int = Query(20, ge=1, le=100, description="結果數量限制"),
    current_user = Depends(get_current_user_optional)
):
    """
    全文搜尋
    
    - **權限**: 公開端點
    - **功能**: 全文搜尋，包含相關性評分
    """
    try:
        user_id = str(current_user.id) if current_user else None
        
        results = await proposal_service.full_text_search(
            keywords=q,
            limit=limit,
            user_id=user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"全文搜尋時發生錯誤: {str(e)}")


@router.get("/my-proposals/", response_model=ProposalListResponse)
async def get_my_proposals(
    status_filter: Optional[List[ProposalStatus]] = Query(None, description="狀態篩選"),
    pagination: PaginationParams = Depends(),
    current_user = Depends(require_roles([UserRole.SELLER, UserRole.ADMIN]))
):
    """
    取得我的提案列表
    
    - **需要權限**: 提案方或管理員
    - **功能**: 查看當前用戶創建的所有提案
    """
    try:
        proposals = await proposal_service.get_proposals_by_creator(
            creator_id=str(current_user.id),
            status_filter=status_filter
        )
        
        # 分頁處理
        total_count = len(proposals)
        start_idx = (pagination.page - 1) * pagination.page_size
        end_idx = start_idx + pagination.page_size
        paginated_proposals = proposals[start_idx:end_idx]
        
        # 格式化結果
        proposal_data = []
        for proposal in paginated_proposals:
            proposal_data.append(await proposal_service.get_proposal_full_info(proposal))
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "proposals": proposal_data,
                    "total_count": total_count,
                    "page_info": {
                        "current_page": pagination.page,
                        "page_size": pagination.page_size,
                        "total_pages": (total_count + pagination.page_size - 1) // pagination.page_size
                    }
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
    提交提案審核
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 將草稿狀態的提案提交給管理員審核
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
                "message": "提案已提交審核"
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proposal_id}/withdraw")
async def withdraw_proposal(
    proposal_id: str,
    reason: Optional[str] = Body(None, embed=True),
    current_user = Depends(get_current_user)
):
    """
    撤回提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 將審核中的提案撤回到草稿狀態
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
                "message": "提案已撤回"
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proposal_id}/archive")
async def archive_proposal(
    proposal_id: str,
    reason: str = Body(..., embed=True),
    current_user = Depends(get_current_user)
):
    """
    歸檔提案
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 將提案歸檔（不再顯示）
    """
    try:
        success = await proposal_service.archive_proposal(
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
                "message": "提案已歸檔"
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{proposal_id}/workflow-history")
async def get_workflow_history(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    取得工作流程歷史
    
    - **需要權限**: 已登入用戶
    - **功能**: 查看提案的狀態變更歷史
    """
    try:
        history = await proposal_service.get_workflow_history(proposal_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": history
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得工作流程歷史時發生錯誤: {str(e)}")


# ==================== 管理員專用端點 ====================

@router.post("/{proposal_id}/approve", dependencies=[Depends(require_admin)])
async def approve_proposal(
    proposal_id: str,
    approve_data: ProposalApproveRequest,
    current_user = Depends(get_current_user)
):
    """
    審核通過提案
    
    - **需要權限**: 管理員
    - **功能**: 審核通過提案，可選擇是否自動發布
    """
    try:
        success = await proposal_service.approve_proposal(
            proposal_id=proposal_id,
            admin_id=str(current_user.id),
            approve_data=approve_data
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="審核提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案審核通過"
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proposal_id}/reject", dependencies=[Depends(require_admin)])
async def reject_proposal(
    proposal_id: str,
    reject_data: ProposalRejectRequest,
    current_user = Depends(get_current_user)
):
    """
    審核拒絕提案
    
    - **需要權限**: 管理員
    - **功能**: 審核拒絕提案，需要提供拒絕原因
    """
    try:
        success = await proposal_service.reject_proposal(
            proposal_id=proposal_id,
            admin_id=str(current_user.id),
            reject_data=reject_data
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="拒絕提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案已被拒絕"
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proposal_id}/publish", dependencies=[Depends(require_admin)])
async def publish_proposal(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    發布提案
    
    - **需要權限**: 管理員
    - **功能**: 將已審核通過的提案發布上線
    """
    try:
        success = await proposal_service.publish_proposal(
            proposal_id=proposal_id,
            admin_id=str(current_user.id)
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="發布提案失敗")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "提案已發布上線"
            }
        )
        
    except (PermissionException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批量操作端點 ====================

@router.post("/batch-approve", dependencies=[Depends(require_admin)])
async def batch_approve_proposals(
    proposal_ids: List[str] = Body(...),
    batch_comment: str = Body("批量審核通過"),
    current_user = Depends(get_current_user)
):
    """
    批量審核通過提案
    
    - **需要權限**: 管理員
    - **功能**: 一次審核通過多個提案
    """
    try:
        results = await proposal_service.batch_approve(
            proposal_ids=proposal_ids,
            admin_id=str(current_user.id),
            batch_comment=batch_comment
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"批量審核完成，成功: {len(results['successful'])}，失敗: {len(results['failed'])}",
                "data": results
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量審核時發生錯誤: {str(e)}")


@router.post("/batch-reject", dependencies=[Depends(require_admin)])
async def batch_reject_proposals(
    proposal_ids: List[str] = Body(...),
    batch_reason: str = Body(...),
    current_user = Depends(get_current_user)
):
    """
    批量審核拒絕提案
    
    - **需要權限**: 管理員
    - **功能**: 一次拒絕多個提案
    """
    try:
        results = await proposal_service.batch_reject(
            proposal_ids=proposal_ids,
            admin_id=str(current_user.id),
            batch_reason=batch_reason
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"批量拒絕完成，成功: {len(results['successful'])}，失敗: {len(results['failed'])}",
                "data": results
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量拒絕時發生錯誤: {str(e)}")


# ==================== 統計和報表端點 ====================

@router.get("/statistics/", response_model=ProposalStatistics, dependencies=[Depends(require_admin)])
async def get_proposal_statistics(
    date_from: Optional[datetime] = Query(None, description="開始日期"),
    date_to: Optional[datetime] = Query(None, description="結束日期"),
    current_user = Depends(get_current_user)
):
    """
    取得提案統計資訊
    
    - **需要權限**: 管理員
    - **功能**: 查看提案的各種統計數據
    """
    try:
        statistics = await proposal_service.get_proposal_statistics(
            date_from=date_from,
            date_to=date_to
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": statistics
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計資訊時發生錯誤: {str(e)}")


@router.get("/admin/pending-reviews/", dependencies=[Depends(require_admin)])
async def get_pending_reviews(
    pagination: PaginationParams = Depends(),
    current_user = Depends(get_current_user)
):
    """
    取得待審核提案列表
    
    - **需要權限**: 管理員
    - **功能**: 查看所有待審核的提案
    """
    try:
        result = await proposal_service.get_pending_reviews(
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得待審核列表時發生錯誤: {str(e)}")


@router.get("/admin/review-history/", dependencies=[Depends(require_admin)])
async def get_review_history(
    admin_id: Optional[str] = Query(None, description="篩選特定管理員"),
    date_from: Optional[datetime] = Query(None, description="開始日期"),
    date_to: Optional[datetime] = Query(None, description="結束日期"),
    pagination: PaginationParams = Depends(),
    current_user = Depends(get_current_user)
):
    """
    取得審核歷史記錄
    
    - **需要權限**: 管理員
    - **功能**: 查看審核歷史，支援篩選和分頁
    """
    try:
        result = await proposal_service.get_review_history(
            admin_id=admin_id,
            date_from=date_from,
            date_to=date_to,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得審核歷史時發生錯誤: {str(e)}")


# ==================== 檔案管理端點 (預留) ====================

@router.post("/{proposal_id}/files")
async def upload_proposal_file(
    proposal_id: str,
    current_user = Depends(get_current_user)
):
    """
    上傳提案附件
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 上傳提案相關檔案 (預留實現)
    """
    # TODO: 實現檔案上傳功能
    raise HTTPException(status_code=501, detail="檔案上傳功能尚未實現")


@router.delete("/{proposal_id}/files/{file_id}")
async def delete_proposal_file(
    proposal_id: str,
    file_id: str,
    current_user = Depends(get_current_user)
):
    """
    刪除提案附件
    
    - **需要權限**: 提案創建者或管理員
    - **功能**: 刪除提案相關檔案 (預留實現)
    """
    # TODO: 實現檔案刪除功能
    raise HTTPException(status_code=501, detail="檔案刪除功能尚未實現")