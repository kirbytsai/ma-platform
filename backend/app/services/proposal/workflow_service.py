"""
提案工作流程服務 - Workflow Service
負責提案狀態的流轉管理和業務流程控制
依賴核心服務和驗證服務
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.exceptions import BusinessException, PermissionException, ValidationException
from app.models.proposal import Proposal, ProposalStatus, ReviewRecord
from app.schemas.proposal import ProposalSubmitRequest


class ProposalWorkflowService:
    """提案工作流程服務類 - 狀態流轉管理"""
    
    def __init__(self, core_service, validation_service):
        """
        初始化工作流程服務
        
        Args:
            core_service: 核心服務實例
            validation_service: 驗證服務實例
        """
        self.core = core_service
        self.validation = validation_service
    
    # ==================== 提案提交流程 ====================
    
    async def submit_proposal(
        self, 
        proposal_id: str, 
        user_id: str, 
        submit_data: Optional[ProposalSubmitRequest] = None
    ) -> bool:
        """
        提交提案進行審核
        
        Args:
            proposal_id: 提案 ID
            user_id: 提交者 ID
            submit_data: 提交相關資料 (可選)
            
        Returns:
            bool: 提交是否成功
            
        Raises:
            BusinessException: 提案狀態不允許提交
            PermissionException: 無提交權限
        """
        try:
            # 取得提案並檢查權限
            proposal = await self.core.get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在或無權限",
                    error_code="PROPOSAL_NOT_FOUND_OR_NO_PERMISSION"
                )
            
            # 檢查當前狀態是否可以提交
            if not proposal.can_submit():
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法提交審核",
                    error_code="PROPOSAL_NOT_SUBMITTABLE"
                )
            
            # 驗證狀態轉換
            await self.validation.validate_status_transition(
                proposal.status, 
                ProposalStatus.UNDER_REVIEW
            )
            
            # 檢查資料完整性
            completeness = await self.validation.check_data_completeness(proposal)
            if not completeness.get("ready_for_submission", False):
                raise ValidationException(
                    message="提案資料不完整，無法提交審核",
                    error_code="PROPOSAL_DATA_INCOMPLETE",
                    details=completeness
                )
            
            # 執行狀態轉換
            success = await self._transition_status(
                proposal_id=proposal_id,
                from_status=proposal.status,
                to_status=ProposalStatus.UNDER_REVIEW,
                operator_id=user_id,
                comment=submit_data.comment if submit_data else "提交審核",
                metadata={
                    "submitted_at": datetime.utcnow(),
                    "submit_data": submit_data.dict() if submit_data else {}
                }
            )
            
            if success:
                # TODO: 發送通知給管理員
                await self._notify_admin_new_submission(proposal_id, user_id)
            
            return success
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException, ValidationException)):
                raise
            raise BusinessException(
                message=f"提交提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_SUBMIT_ERROR"
            )
    
    async def withdraw_proposal(
        self, 
        proposal_id: str, 
        user_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        撤回提案 (從審核中撤回到草稿)
        
        Args:
            proposal_id: 提案 ID
            user_id: 撤回者 ID
            reason: 撤回原因 (可選)
            
        Returns:
            bool: 撤回是否成功
        """
        try:
            # 取得提案並檢查權限
            proposal = await self.core.get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在或無權限",
                    error_code="PROPOSAL_NOT_FOUND_OR_NO_PERMISSION"
                )
            
            # 只有審核中的提案可以撤回
            if proposal.status != ProposalStatus.UNDER_REVIEW:
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法撤回",
                    error_code="PROPOSAL_NOT_WITHDRAWABLE"
                )
            
            # 驗證狀態轉換
            await self.validation.validate_status_transition(
                proposal.status, 
                ProposalStatus.DRAFT
            )
            
            # 執行狀態轉換
            success = await self._transition_status(
                proposal_id=proposal_id,
                from_status=proposal.status,
                to_status=ProposalStatus.DRAFT,
                operator_id=user_id,
                comment=reason or "提案撤回",
                metadata={
                    "withdrawn_at": datetime.utcnow(),
                    "reason": reason
                }
            )
            
            return success
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"撤回提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_WITHDRAW_ERROR"
            )
    
    async def publish_proposal(
        self, 
        proposal_id: str, 
        admin_id: str
    ) -> bool:
        """
        發布提案 (從已審核變為可瀏覽)
        
        Args:
            proposal_id: 提案 ID
            admin_id: 管理員 ID
            
        Returns:
            bool: 發布是否成功
        """
        try:
            # 檢查管理員權限
            await self.validation.check_admin_permission(admin_id)
            
            # 取得提案
            proposal = await self.core.get_proposal_by_id(proposal_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在",
                    error_code="PROPOSAL_NOT_FOUND"
                )
            
            # 只有已審核通過的提案可以發布
            if proposal.status != ProposalStatus.APPROVED:
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法發布",
                    error_code="PROPOSAL_NOT_PUBLISHABLE"
                )
            
            # 驗證狀態轉換
            await self.validation.validate_status_transition(
                proposal.status, 
                ProposalStatus.AVAILABLE
            )
            
            # 執行狀態轉換
            success = await self._transition_status(
                proposal_id=proposal_id,
                from_status=proposal.status,
                to_status=ProposalStatus.AVAILABLE,
                operator_id=admin_id,
                comment="提案發布上線",
                metadata={
                    "published_at": datetime.utcnow(),
                    "published_by": admin_id
                }
            )
            
            if success:
                # TODO: 通知創建者
                await self._notify_creator_published(proposal_id, admin_id)
            
            return success
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"發布提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_PUBLISH_ERROR"
            )
    
    async def archive_proposal(
        self, 
        proposal_id: str, 
        user_id: str,
        reason: str
    ) -> bool:
        """
        歸檔提案
        
        Args:
            proposal_id: 提案 ID
            user_id: 操作者 ID
            reason: 歸檔原因
            
        Returns:
            bool: 歸檔是否成功
        """
        try:
            # 取得提案
            proposal = await self.core.get_proposal_by_id(proposal_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在",
                    error_code="PROPOSAL_NOT_FOUND"
                )
            
            # 檢查權限 (創建者或管理員)
            is_creator = str(proposal.creator_id) == user_id
            is_admin = False
            
            if not is_creator:
                try:
                    await self.validation.check_admin_permission(user_id)
                    is_admin = True
                except PermissionException:
                    raise PermissionException(
                        message="只有創建者或管理員可以歸檔提案",
                        error_code="PROPOSAL_ARCHIVE_NO_PERMISSION"
                    )
            
            # 檢查是否已經歸檔
            if proposal.status == ProposalStatus.ARCHIVED:
                raise BusinessException(
                    message="提案已經歸檔",
                    error_code="PROPOSAL_ALREADY_ARCHIVED"
                )
            
            # 執行狀態轉換
            success = await self._transition_status(
                proposal_id=proposal_id,
                from_status=proposal.status,
                to_status=ProposalStatus.ARCHIVED,
                operator_id=user_id,
                comment=reason,
                metadata={
                    "archived_at": datetime.utcnow(),
                    "archived_by": "admin" if is_admin else "creator",
                    "reason": reason
                }
            )
            
            return success
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"歸檔提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_ARCHIVE_ERROR"
            )
    
    # ==================== 狀態查詢和檢查 ====================
    
    async def can_transition_to(
        self, 
        proposal_id: str, 
        target_status: ProposalStatus,
        user_id: str
    ) -> Dict[str, Any]:
        """
        檢查提案是否可以轉換到指定狀態
        
        Args:
            proposal_id: 提案 ID
            target_status: 目標狀態
            user_id: 操作者 ID
            
        Returns:
            Dict[str, Any]: 檢查結果
        """
        try:
            proposal = await self.core.get_proposal_by_id(proposal_id)
            if not proposal:
                return {
                    "can_transition": False,
                    "reason": "提案不存在",
                    "error_code": "PROPOSAL_NOT_FOUND"
                }
            
            # 檢查權限
            permissions = await self.validation.check_view_permission(proposal, user_id)
            
            # 檢查狀態轉換規則
            try:
                await self.validation.validate_status_transition(
                    proposal.status, 
                    target_status
                )
                
                return {
                    "can_transition": True,
                    "current_status": proposal.status,
                    "target_status": target_status,
                    "permissions": permissions
                }
                
            except ValidationException as e:
                return {
                    "can_transition": False,
                    "reason": e.message,
                    "error_code": e.error_code,
                    "current_status": proposal.status,
                    "target_status": target_status
                }
                
        except Exception as e:
            return {
                "can_transition": False,
                "reason": f"檢查狀態轉換時發生錯誤: {str(e)}",
                "error_code": "STATUS_TRANSITION_CHECK_ERROR"
            }
    
    async def get_workflow_history(self, proposal_id: str) -> List[Dict[str, Any]]:
        """
        取得提案的工作流程歷史
        
        Args:
            proposal_id: 提案 ID
            
        Returns:
            List[Dict[str, Any]]: 工作流程歷史記錄
        """
        try:
            proposal = await self.core.get_proposal_by_id(proposal_id)
            if not proposal:
                return []
            
            # 取得審核記錄
            history = []
            for record in proposal.review_records:
                history.append({
                    "action": record.action,
                    "status_from": record.status_from,
                    "status_to": record.status_to,
                    "reviewer_id": str(record.reviewer_id),
                    "comment": record.comment,
                    "created_at": record.created_at,
                    "metadata": record.metadata
                })
            
            # 按時間排序
            history.sort(key=lambda x: x["created_at"], reverse=True)
            
            return history
            
        except Exception as e:
            raise BusinessException(
                message=f"取得工作流程歷史時發生錯誤: {str(e)}",
                error_code="WORKFLOW_HISTORY_ERROR"
            )
    
    # ==================== 私有方法 ====================
    
    async def _transition_status(
        self,
        proposal_id: str,
        from_status: ProposalStatus,
        to_status: ProposalStatus,
        operator_id: str,
        comment: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        執行狀態轉換
        
        Args:
            proposal_id: 提案 ID
            from_status: 源狀態
            to_status: 目標狀態
            operator_id: 操作者 ID
            comment: 操作註釋
            metadata: 額外資料
            
        Returns:
            bool: 轉換是否成功
        """
        try:
            collection = await self.core._get_collection()
            
            # 建立審核記錄
            review_record = ReviewRecord(
                action=f"{from_status}_to_{to_status}",
                status_from=from_status,
                status_to=to_status,
                reviewer_id=ObjectId(operator_id),
                comment=comment,
                created_at=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # 執行狀態更新和添加審核記錄
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$set": {
                        "status": to_status,
                        "updated_at": datetime.utcnow()
                    },
                    "$push": {"review_records": review_record.to_dict()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise BusinessException(
                message=f"執行狀態轉換時發生錯誤: {str(e)}",
                error_code="STATUS_TRANSITION_ERROR"
            )
    
    async def _notify_admin_new_submission(self, proposal_id: str, creator_id: str):
        """
        通知管理員有新的提案提交 (預留實現)
        
        TODO: 實現通知系統後完整實現
        """
        # 預留給通知系統實現
        print(f"新提案提交通知: 提案 {proposal_id} 由用戶 {creator_id} 提交審核")
    
    async def _notify_creator_published(self, proposal_id: str, admin_id: str):
        """
        通知創建者提案已發布 (預留實現)
        
        TODO: 實現通知系統後完整實現
        """
        # 預留給通知系統實現
        print(f"提案發布通知: 提案 {proposal_id} 已由管理員 {admin_id} 發布上線")