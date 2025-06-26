"""
提案核心服務 - Core Service
負責提案的基本 CRUD 操作和檔案管理
這是其他服務模組的基礎依賴
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.core.database import Database
from app.core.exceptions import BusinessException, PermissionDeniedException
from app.models.proposal import (
    Proposal, ProposalStatus, CompanyInfo, FinancialInfo, 
    BusinessModel, TeaserContent, FullContent
)
from app.models.user import UserRole
from app.schemas.proposal import ProposalCreate, ProposalUpdate


class ProposalCoreService:
    """提案核心服務類 - 基礎 CRUD 操作"""
    
    def __init__(self, validation_service=None):
        """
        初始化核心服務
        
        Args:
            validation_service: 驗證服務實例 (可選，用於依賴注入)
        """
        self.database = None
        self.validation_service = validation_service
        
    async def _get_database(self) -> AsyncIOMotorDatabase:
        """取得資料庫實例"""
        if self.database is None:
            self.database = Database.get_database()
        return self.database
    
    async def _get_collection(self) -> AsyncIOMotorCollection:
        """取得提案集合"""
        database = await self._get_database()
        return database.proposals
    
    async def _get_user_collection(self) -> AsyncIOMotorCollection:
        """取得用戶集合"""
        database = await self._get_database()
        return database.users
    
    # ==================== 基礎 CRUD 操作 ====================
    
    async def create_proposal(
        self, 
        creator_id: str, 
        proposal_data: ProposalCreate
    ) -> Proposal:
        """
        創建新提案
        
        Args:
            creator_id: 創建者 ID
            proposal_data: 提案創建資料
            
        Returns:
            Proposal: 創建的提案實例
            
        Raises:
            PermissionDeniedException: 創建者權限不足
            BusinessException: 創建失敗
        """
        try:
            # 驗證創建者權限
            if self.validation_service:
                await self.validation_service.check_creator_permission(creator_id)
            else:
                await self._check_creator_permission_basic(creator_id)
            
            # 創建提案實例
            proposal = Proposal(
                creator_id=ObjectId(creator_id),
                company_info=CompanyInfo(**proposal_data.company_info.dict()),
                financial_info=FinancialInfo(**proposal_data.financial_info.dict()),
                business_model=BusinessModel(**proposal_data.business_model.dict()),
                teaser_content=TeaserContent(**proposal_data.teaser_content.dict()),
                full_content=FullContent(**proposal_data.full_content.dict()) if proposal_data.full_content else None,
                status=ProposalStatus.DRAFT,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # 儲存到資料庫
            collection = await self._get_collection()
            result = await collection.insert_one(proposal.to_dict())
            
            if not result.inserted_id:
                raise BusinessException(
                    message="提案創建失敗",
                    error_code="PROPOSAL_CREATE_FAILED"
                )
            
            # 設定 ID 並返回
            proposal.id = result.inserted_id
            return proposal
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionDeniedException)):
                raise
            raise BusinessException(
                message=f"創建提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_CREATE_ERROR"
            )
    
    async def get_proposal_by_id(
        self, 
        proposal_id: str, 
        user_id: Optional[str] = None,
        increment_view: bool = False
    ) -> Optional[Proposal]:
        """
        根據 ID 取得提案
        
        Args:
            proposal_id: 提案 ID
            user_id: 查看者 ID (可選，用於權限檢查)
            increment_view: 是否增加瀏覽量
            
        Returns:
            Optional[Proposal]: 提案實例或 None
        """
        try:
            collection = await self._get_collection()
            
            # 查詢提案
            proposal_dict = await collection.find_one({"_id": ObjectId(proposal_id)})
            if not proposal_dict:
                return None
            
            # 轉換為提案實例
            proposal = Proposal.from_dict(proposal_dict)
            
            # 增加瀏覽量 (如果需要且不是創建者)
            if increment_view and user_id and str(proposal.creator_id) != user_id:
                await self.increment_view_count(proposal_id)
                proposal.view_count += 1
            
            return proposal
            
        except Exception as e:
            raise BusinessException(
                message=f"查詢提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_GET_ERROR"
            )
    
    async def get_proposal_for_edit(
        self, 
        proposal_id: str, 
        user_id: str
    ) -> Optional[Proposal]:
        """
        取得用於編輯的提案 (包含權限檢查)
        
        Args:
            proposal_id: 提案 ID
            user_id: 編輯者 ID
            
        Returns:
            Optional[Proposal]: 可編輯的提案實例或 None
            
        Raises:
            PermissionDeniedException: 無編輯權限
        """
        proposal = await self.get_proposal_by_id(proposal_id)
        if not proposal:
            return None
        
        # 檢查編輯權限
        if str(proposal.creator_id) != user_id:
            # 檢查是否是管理員
            user_collection = await self._get_user_collection()
            user = await user_collection.find_one({"_id": ObjectId(user_id)})
            
            if not user or user.get("role") != UserRole.ADMIN:
                raise PermissionDeniedException(
                    message="無權限編輯此提案",
                    error_code="PROPOSAL_EDIT_NO_PERMISSION"
                )
        
        return proposal
    
    async def update_proposal(
        self, 
        proposal_id: str, 
        user_id: str, 
        update_data: ProposalUpdate
    ) -> bool:
        """
        更新提案基本資訊
        
        Args:
            proposal_id: 提案 ID
            user_id: 更新者 ID
            update_data: 更新資料
            
        Returns:
            bool: 更新是否成功
            
        Raises:
            BusinessException: 提案不存在或無法編輯
            PermissionDeniedException: 無編輯權限
        """
        try:
            # 驗證提案存在且用戶有權限
            proposal = await self.get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在或無權限",
                    error_code="PROPOSAL_NOT_FOUND_OR_NO_PERMISSION"
                )
            
            # 檢查是否可以編輯
            if not proposal.can_edit():
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法編輯",
                    error_code="PROPOSAL_NOT_EDITABLE"
                )
            
            # 準備更新資料
            update_dict = {"updated_at": datetime.utcnow()}
            
            # 更新各個區塊
            if update_data.company_info:
                update_dict["company_info"] = update_data.company_info.dict()
            
            if update_data.financial_info:
                update_dict["financial_info"] = update_data.financial_info.dict()
            
            if update_data.business_model:
                update_dict["business_model"] = update_data.business_model.dict()
            
            if update_data.teaser_content:
                update_dict["teaser_content"] = update_data.teaser_content.dict()
            
            if update_data.full_content:
                update_dict["full_content"] = update_data.full_content.dict()
            
            # 執行更新
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {"$set": update_dict}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionDeniedException)):
                raise
            raise BusinessException(
                message=f"更新提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_UPDATE_ERROR"
            )
    
    async def delete_proposal(
        self, 
        proposal_id: str, 
        user_id: str
    ) -> bool:
        """
        刪除提案 (軟刪除)
        
        Args:
            proposal_id: 提案 ID
            user_id: 刪除者 ID
            
        Returns:
            bool: 刪除是否成功
        """
        try:
            # 驗證提案存在且用戶有權限
            proposal = await self.get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在或無權限",
                    error_code="PROPOSAL_NOT_FOUND_OR_NO_PERMISSION"
                )
            
            # 檢查是否可以刪除 (只有草稿或被拒絕的提案可以刪除)
            if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.REJECTED]:
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法刪除",
                    error_code="PROPOSAL_NOT_DELETABLE"
                )
            
            # 執行軟刪除
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$set": {
                        "status": ProposalStatus.ARCHIVED,
                        "updated_at": datetime.utcnow(),
                        "deleted_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionDeniedException)):
                raise
            raise BusinessException(
                message=f"刪除提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_DELETE_ERROR"
            )
    
    # ==================== 檔案管理 ====================
    
    async def add_proposal_file(
        self, 
        proposal_id: str, 
        user_id: str, 
        file_info: Dict[str, Any]
    ) -> bool:
        """
        添加提案附件
        
        Args:
            proposal_id: 提案 ID
            user_id: 上傳者 ID
            file_info: 檔案資訊
            
        Returns:
            bool: 添加是否成功
        """
        try:
            # 驗證提案存在且用戶有權限
            proposal = await self.get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在或無權限",
                    error_code="PROPOSAL_NOT_FOUND_OR_NO_PERMISSION"
                )
            
            # 檢查是否可以編輯
            if not proposal.can_edit():
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法添加檔案",
                    error_code="PROPOSAL_NOT_EDITABLE"
                )
            
            # 準備檔案記錄
            file_record = {
                "file_id": ObjectId(),
                "file_name": file_info.get("filename"),
                "file_type": file_info.get("content_type"),
                "file_size": file_info.get("size"),
                "upload_time": datetime.utcnow(),
                "uploaded_by": ObjectId(user_id)
            }
            
            # 添加檔案記錄
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$push": {"attached_files": file_record},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionDeniedException)):
                raise
            raise BusinessException(
                message=f"添加檔案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_FILE_ADD_ERROR"
            )
    
    async def remove_proposal_file(
        self, 
        proposal_id: str, 
        file_id: str, 
        user_id: str
    ) -> bool:
        """
        移除提案附件
        
        Args:
            proposal_id: 提案 ID
            file_id: 檔案 ID
            user_id: 操作者 ID
            
        Returns:
            bool: 移除是否成功
        """
        try:
            # 驗證提案存在且用戶有權限
            proposal = await self.get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在或無權限",
                    error_code="PROPOSAL_NOT_FOUND_OR_NO_PERMISSION"
                )
            
            # 檢查是否可以編輯
            if not proposal.can_edit():
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法移除檔案",
                    error_code="PROPOSAL_NOT_EDITABLE"
                )
            
            # 移除檔案記錄
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$pull": {"attached_files": {"file_id": ObjectId(file_id)}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionDeniedException)):
                raise
            raise BusinessException(
                message=f"移除檔案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_FILE_REMOVE_ERROR"
            )
    
    # ==================== 統計和輔助功能 ====================
    
    async def increment_view_count(self, proposal_id: str) -> bool:
        """
        增加提案瀏覽量
        
        Args:
            proposal_id: 提案 ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {"$inc": {"view_count": 1}}
            )
            return result.modified_count > 0
            
        except Exception as e:
            # 瀏覽量統計失敗不影響主功能，記錄日誌即可
            print(f"增加瀏覽量失敗: {str(e)}")
            return False
    
    async def get_proposals_by_creator(
        self, 
        creator_id: str, 
        status_filter: Optional[List[ProposalStatus]] = None
    ) -> List[Proposal]:
        """
        取得創建者的所有提案
        
        Args:
            creator_id: 創建者 ID
            status_filter: 狀態篩選 (可選)
            
        Returns:
            List[Proposal]: 提案列表
        """
        try:
            collection = await self._get_collection()
            
            # 建構查詢條件
            query = {"creator_id": ObjectId(creator_id)}
            if status_filter:
                query["status"] = {"$in": status_filter}
            
            # 查詢並排序
            cursor = collection.find(query).sort("created_at", -1)
            proposals = []
            
            async for proposal_dict in cursor:
                proposals.append(Proposal.from_dict(proposal_dict))
            
            return proposals
            
        except Exception as e:
            raise BusinessException(
                message=f"查詢創建者提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_GET_BY_CREATOR_ERROR"
            )
    
    # ==================== 私有輔助方法 ====================
    
    async def _check_creator_permission_basic(self, user_id: str) -> None:
        """
        基礎創建者權限檢查 (當沒有驗證服務時使用)
        
        Args:
            user_id: 用戶 ID
            
        Raises:
            PermissionDeniedException: 權限不足
        """
        try:
            user_collection = await self._get_user_collection()
            user = await user_collection.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                raise PermissionDeniedException(
                    message="用戶不存在",
                    error_code="USER_NOT_FOUND"
                )
            
            if user.get("role") not in [UserRole.SELLER, UserRole.ADMIN]:
                raise PermissionDeniedException(
                    message="只有提案方和管理員可以創建提案",
                    error_code="PROPOSAL_CREATE_NO_PERMISSION"
                )
                
        except Exception as e:
            if isinstance(e, PermissionDeniedException):
                raise
            raise PermissionDeniedException(
                message=f"檢查創建權限時發生錯誤: {str(e)}",
                error_code="PERMISSION_CHECK_ERROR"
            )