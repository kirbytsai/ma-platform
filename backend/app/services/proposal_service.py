"""
提案系統業務邏輯服務層
處理提案的 CRUD 操作、狀態管理、權限控制、搜尋篩選等核心業務邏輯
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
import re
from math import ceil

from app.core.database import Database
from app.core.exceptions import BusinessException, ValidationException, PermissionException
from app.models.proposal import (
    Proposal, ProposalStatus, Industry, CompanySize,
    CompanyInfo, FinancialInfo, BusinessModel, 
    TeaserContent, FullContent, ReviewRecord
)
from app.models.user import UserRole
from app.schemas.proposal import (
    ProposalCreate, ProposalUpdate, ProposalSearchParams,
    ProposalSubmitRequest, ProposalApproveRequest, ProposalRejectRequest
)


class ProposalService:
    """提案服務類"""
    
    def __init__(self):
        self.database = None
        
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
        """創建提案"""
        try:
            # 驗證創建者權限
            await self._validate_creator_permission(creator_id)
            
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
            
            # 返回創建的提案
            proposal.id = result.inserted_id
            return proposal
            
        except Exception as e:
            if isinstance(e, (BusinessException, ValidationException)):
                raise
            raise BusinessException(
                message=f"創建提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_CREATE_ERROR"
            )
    
    async def get_proposal_by_id(
        self, 
        proposal_id: str, 
        user_id: str, 
        user_role: str
    ) -> Optional[Proposal]:
        """根據 ID 取得提案"""
        try:
            collection = await self._get_collection()
            proposal_data = await collection.find_one({"_id": ObjectId(proposal_id)})
            
            if not proposal_data:
                return None
            
            proposal = Proposal(**proposal_data)
            
            # 權限檢查
            await self._validate_read_permission(proposal, user_id, user_role)
            
            # 增加瀏覽次數 (非創建者瀏覽時)
            if str(proposal.creator_id) != user_id:
                await self._increment_view_count(proposal_id)
            
            return proposal
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"取得提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_GET_ERROR"
            )
    
    async def update_proposal(
        self, 
        proposal_id: str, 
        user_id: str, 
        update_data: ProposalUpdate
    ) -> Optional[Proposal]:
        """更新提案"""
        try:
            # 取得現有提案
            proposal = await self._get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                return None
            
            # 檢查是否可以編輯
            if not proposal.can_edit():
                raise PermissionException(
                    message=f"提案狀態為 {proposal.status}，無法編輯",
                    error_code="PROPOSAL_NOT_EDITABLE"
                )
            
            # 準備更新資料
            update_dict = {"updated_at": datetime.utcnow()}
            
            if update_data.company_info:
                update_dict["company_info"] = CompanyInfo(**update_data.company_info.dict()).dict()
            
            if update_data.financial_info:
                update_dict["financial_info"] = FinancialInfo(**update_data.financial_info.dict()).dict()
            
            if update_data.business_model:
                update_dict["business_model"] = BusinessModel(**update_data.business_model.dict()).dict()
            
            if update_data.teaser_content:
                update_dict["teaser_content"] = TeaserContent(**update_data.teaser_content.dict()).dict()
            
            if update_data.full_content:
                update_dict["full_content"] = FullContent(**update_data.full_content.dict()).dict()
            
            # 執行更新
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count == 0:
                return None
            
            # 返回更新後的提案
            return await self._get_proposal_for_edit(proposal_id, user_id)
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException, ValidationException)):
                raise
            raise BusinessException(
                message=f"更新提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_UPDATE_ERROR"
            )
    
    async def delete_proposal(self, proposal_id: str, user_id: str) -> bool:
        """軟刪除提案"""
        try:
            # 取得現有提案
            proposal = await self._get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                return False
            
            # 檢查是否可以刪除 (只有草稿狀態可以刪除)
            if proposal.status != ProposalStatus.DRAFT:
                raise PermissionException(
                    message=f"提案狀態為 {proposal.status}，無法刪除",
                    error_code="PROPOSAL_NOT_DELETABLE"
                )
            
            # 軟刪除 (設為不啟用)
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"刪除提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_DELETE_ERROR"
            )
    
    # ==================== 狀態管理操作 ====================
    
    async def submit_proposal(
        self, 
        proposal_id: str, 
        user_id: str, 
        submit_data: ProposalSubmitRequest
    ) -> bool:
        """提交提案審核"""
        try:
            # 取得現有提案
            proposal = await self._get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在",
                    error_code="PROPOSAL_NOT_FOUND"
                )
            
            # 檢查是否可以提交
            if not proposal.can_submit():
                raise PermissionException(
                    message=f"提案狀態為 {proposal.status}，無法提交審核",
                    error_code="PROPOSAL_NOT_SUBMITTABLE"
                )
            
            # 更新完整內容和狀態
            update_dict = {
                "full_content": FullContent(**submit_data.full_content.dict()).dict(),
                "status": ProposalStatus.UNDER_REVIEW,
                "submitted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {"$set": update_dict}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException, ValidationException)):
                raise
            raise BusinessException(
                message=f"提交提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_SUBMIT_ERROR"
            )
    
    async def approve_proposal(
        self, 
        proposal_id: str, 
        reviewer_id: str, 
        reviewer_name: str,
        approve_data: ProposalApproveRequest
    ) -> bool:
        """核准提案"""
        try:
            # 取得提案
            proposal = await self._get_proposal_by_id_raw(proposal_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在",
                    error_code="PROPOSAL_NOT_FOUND"
                )
            
            # 檢查是否可以核准
            if not proposal.can_approve():
                raise PermissionException(
                    message=f"提案狀態為 {proposal.status}，無法核准",
                    error_code="PROPOSAL_NOT_APPROVABLE"
                )
            
            # 創建審核記錄
            review_record = ReviewRecord(
                reviewer_id=ObjectId(reviewer_id),
                reviewer_name=reviewer_name,
                action="approve",
                comment=approve_data.comment,
                reviewed_at=datetime.utcnow()
            )
            
            # 更新提案狀態
            update_dict = {
                "status": ProposalStatus.APPROVED,
                "approved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "$push": {"review_records": review_record.dict()}
            }
            
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                update_dict
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"核准提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_APPROVE_ERROR"
            )
    
    async def reject_proposal(
        self, 
        proposal_id: str, 
        reviewer_id: str, 
        reviewer_name: str,
        reject_data: ProposalRejectRequest
    ) -> bool:
        """拒絕提案"""
        try:
            # 取得提案
            proposal = await self._get_proposal_by_id_raw(proposal_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在",
                    error_code="PROPOSAL_NOT_FOUND"
                )
            
            # 檢查是否可以拒絕
            if not proposal.can_approve():  # 和核准使用相同的狀態檢查
                raise PermissionException(
                    message=f"提案狀態為 {proposal.status}，無法拒絕",
                    error_code="PROPOSAL_NOT_REJECTABLE"
                )
            
            # 創建審核記錄
            review_record = ReviewRecord(
                reviewer_id=ObjectId(reviewer_id),
                reviewer_name=reviewer_name,
                action="reject",
                comment=reject_data.reason,
                reviewed_at=datetime.utcnow()
            )
            
            # 更新提案狀態
            update_dict = {
                "status": ProposalStatus.REJECTED,
                "rejection_reason": reject_data.reason,
                "updated_at": datetime.utcnow(),
                "$push": {"review_records": review_record.dict()}
            }
            
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                update_dict
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"拒絕提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_REJECT_ERROR"
            )
    
    async def publish_proposal(self, proposal_id: str) -> bool:
        """發布提案 (核准後可發送)"""
        try:
            # 取得提案
            proposal = await self._get_proposal_by_id_raw(proposal_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在",
                    error_code="PROPOSAL_NOT_FOUND"
                )
            
            # 檢查是否可以發布
            if proposal.status != ProposalStatus.APPROVED:
                raise PermissionException(
                    message=f"只有已核准的提案才能發布，當前狀態: {proposal.status}",
                    error_code="PROPOSAL_NOT_PUBLISHABLE"
                )
            
            # 更新狀態
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$set": {
                        "status": ProposalStatus.AVAILABLE,
                        "published_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"發布提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_PUBLISH_ERROR"
            )
    
    # ==================== 搜尋和列表操作 ====================
    
    async def search_proposals(
        self, 
        search_params: ProposalSearchParams,
        user_id: str,
        user_role: str
    ) -> Tuple[List[Proposal], int]:
        """搜尋提案"""
        try:
            collection = await self._get_collection()
            
            # 建立查詢條件
            query = await self._build_search_query(search_params, user_id, user_role)
            
            # 建立排序條件
            sort_condition = await self._build_sort_condition(search_params)
            
            # 計算分頁
            skip = (search_params.page - 1) * search_params.size
            
            # 執行查詢
            cursor = collection.find(query).sort(sort_condition).skip(skip).limit(search_params.size)
            proposals_data = await cursor.to_list(length=search_params.size)
            
            # 計算總數
            total = await collection.count_documents(query)
            
            # 轉換為 Proposal 物件
            proposals = []
            for proposal_data in proposals_data:
                proposal = Proposal(**proposal_data)
                proposals.append(proposal)
            
            return proposals, total
            
        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            raise BusinessException(
                message=f"搜尋提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_SEARCH_ERROR"
            )
    
    async def get_user_proposals(
        self, 
        creator_id: str, 
        page: int = 1, 
        size: int = 10
    ) -> Tuple[List[Proposal], int]:
        """取得用戶的提案列表"""
        try:
            collection = await self._get_collection()
            
            query = {
                "creator_id": ObjectId(creator_id),
                "is_active": True
            }
            
            skip = (page - 1) * size
            
            # 執行查詢 (按創建時間倒序)
            cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(size)
            proposals_data = await cursor.to_list(length=size)
            
            # 計算總數
            total = await collection.count_documents(query)
            
            # 轉換為 Proposal 物件
            proposals = []
            for proposal_data in proposals_data:
                proposal = Proposal(**proposal_data)
                proposals.append(proposal)
            
            return proposals, total
            
        except Exception as e:
            raise BusinessException(
                message=f"取得用戶提案時發生錯誤: {str(e)}",
                error_code="USER_PROPOSALS_GET_ERROR"
            )
    
    async def get_pending_proposals(
        self, 
        page: int = 1, 
        size: int = 10
    ) -> Tuple[List[Proposal], int]:
        """取得待審核提案列表 (管理員用)"""
        try:
            collection = await self._get_collection()
            
            query = {
                "status": ProposalStatus.UNDER_REVIEW,
                "is_active": True
            }
            
            skip = (page - 1) * size
            
            # 執行查詢 (按提交時間順序)
            cursor = collection.find(query).sort("submitted_at", 1).skip(skip).limit(size)
            proposals_data = await cursor.to_list(length=size)
            
            # 計算總數
            total = await collection.count_documents(query)
            
            # 轉換為 Proposal 物件
            proposals = []
            for proposal_data in proposals_data:
                proposal = Proposal(**proposal_data)
                proposals.append(proposal)
            
            return proposals, total
            
        except Exception as e:
            raise BusinessException(
                message=f"取得待審核提案時發生錯誤: {str(e)}",
                error_code="PENDING_PROPOSALS_GET_ERROR"
            )
    
    # ==================== 統計操作 ====================
    
    async def get_proposal_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """取得提案統計資料"""
        try:
            collection = await self._get_collection()
            
            # 基礎查詢條件
            base_query = {"is_active": True}
            if user_id:
                base_query["creator_id"] = ObjectId(user_id)
            
            # 狀態統計
            stats = {}
            for status in ProposalStatus:
                query = {**base_query, "status": status}
                stats[f"{status}_count"] = await collection.count_documents(query)
            
            # 總計
            stats["total_proposals"] = await collection.count_documents(base_query)
            
            # 互動統計
            pipeline = [
                {"$match": base_query},
                {"$group": {
                    "_id": None,
                    "total_views": {"$sum": "$view_count"},
                    "total_sent": {"$sum": "$sent_count"},
                    "total_interest": {"$sum": "$interest_count"}
                }}
            ]
            
            interaction_stats = await collection.aggregate(pipeline).to_list(1)
            if interaction_stats:
                stats.update(interaction_stats[0])
                del stats["_id"]
            else:
                stats.update({
                    "total_views": 0,
                    "total_sent": 0,
                    "total_interest": 0
                })
            
            # 行業分佈
            pipeline = [
                {"$match": base_query},
                {"$group": {
                    "_id": "$company_info.industry",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            
            industry_stats = await collection.aggregate(pipeline).to_list(None)
            stats["industry_distribution"] = {
                item["_id"]: item["count"] for item in industry_stats
            }
            
            # 月度創建趨勢 (最近6個月)
            pipeline = [
                {"$match": base_query},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id.year": 1, "_id.month": 1}},
                {"$limit": 6}
            ]
            
            monthly_stats = await collection.aggregate(pipeline).to_list(6)
            stats["monthly_creation_trend"] = [
                {
                    "month": f"{item['_id']['year']}-{item['_id']['month']:02d}",
                    "count": item["count"]
                }
                for item in monthly_stats
            ]
            
            return stats
            
        except Exception as e:
            raise BusinessException(
                message=f"取得統計資料時發生錯誤: {str(e)}",
                error_code="PROPOSAL_STATS_ERROR"
            )
    
    # ==================== 輔助方法 ====================
    
    async def _validate_creator_permission(self, creator_id: str):
        """驗證創建者權限"""
        user_collection = await self._get_user_collection()
        user = await user_collection.find_one({"_id": ObjectId(creator_id)})
        
        if not user:
            raise BusinessException(
                message="用戶不存在",
                error_code="USER_NOT_FOUND"
            )
        
        if user.get("role") != UserRole.SELLER:
            raise PermissionException(
                message="只有提案方可以創建提案",
                error_code="INSUFFICIENT_PERMISSION"
            )
        
        if not user.get("is_active", False):
            raise PermissionException(
                message="帳號未啟用，無法創建提案",
                error_code="ACCOUNT_DISABLED"
            )
    
    async def _validate_read_permission(self, proposal: Proposal, user_id: str, user_role: str):
        """驗證讀取權限"""
        # 創建者可以查看自己的提案
        if str(proposal.creator_id) == user_id:
            return
        
        # 管理員可以查看所有提案
        if user_role == UserRole.ADMIN:
            return
        
        # 買方只能查看已發布的提案
        if user_role == UserRole.BUYER:
            if proposal.status not in [ProposalStatus.AVAILABLE, ProposalStatus.SENT]:
                raise PermissionException(
                    message="此提案尚未發布，無法查看",
                    error_code="PROPOSAL_NOT_AVAILABLE"
                )
            return
        
        # 其他情況拒絕存取
        raise PermissionException(
            message="無權限查看此提案",
            error_code="INSUFFICIENT_PERMISSION"
        )
    
    async def _get_proposal_for_edit(self, proposal_id: str, user_id: str) -> Optional[Proposal]:
        """取得可編輯的提案 (僅創建者)"""
        collection = await self._get_collection()
        proposal_data = await collection.find_one({
            "_id": ObjectId(proposal_id),
            "creator_id": ObjectId(user_id),
            "is_active": True
        })
        
        if not proposal_data:
            return None
        
        return Proposal(**proposal_data)
    
    async def _get_proposal_by_id_raw(self, proposal_id: str) -> Optional[Proposal]:
        """取得提案 (無權限檢查)"""
        collection = await self._get_collection()
        proposal_data = await collection.find_one({"_id": ObjectId(proposal_id)})
        
        if not proposal_data:
            return None
        
        return Proposal(**proposal_data)
    
    async def _increment_view_count(self, proposal_id: str):
        """增加瀏覽次數"""
        try:
            collection = await self._get_collection()
            await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$inc": {"view_count": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
        except Exception:
            # 瀏覽次數更新失敗不應該影響主要功能
            pass
    
    async def _build_search_query(
        self, 
        search_params: ProposalSearchParams,
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """建立搜尋查詢條件"""
        query = {"is_active": True}
        
        # 根據角色限制可見範圍
        if user_role == UserRole.SELLER:
            # 提案方只能看到自己的提案
            query["creator_id"] = ObjectId(user_id)
        elif user_role == UserRole.BUYER:
            # 買方只能看到已發布的提案
            query["status"] = {"$in": [ProposalStatus.AVAILABLE, ProposalStatus.SENT]}
        # 管理員可以看到所有提案
        
        # 關鍵字搜尋
        if search_params.keyword:
            keyword_regex = re.compile(search_params.keyword, re.IGNORECASE)
            query["$or"] = [
                {"company_info.company_name": keyword_regex},
                {"teaser_content.title": keyword_regex},
                {"teaser_content.summary": keyword_regex}
            ]
        
        # 狀態篩選
        if search_params.status:
            query["status"] = {"$in": search_params.status}
        
        # 行業篩選
        if search_params.industries:
            query["company_info.industry"] = {"$in": search_params.industries}
        
        # 財務範圍篩選
        if search_params.min_revenue is not None or search_params.max_revenue is not None:
            revenue_filter = {}
            if search_params.min_revenue is not None:
                revenue_filter["$gte"] = search_params.min_revenue
            if search_params.max_revenue is not None:
                revenue_filter["$lte"] = search_params.max_revenue
            query["financial_info.annual_revenue"] = revenue_filter
        
        if search_params.min_asking_price is not None or search_params.max_asking_price is not None:
            price_filter = {}
            if search_params.min_asking_price is not None:
                price_filter["$gte"] = search_params.min_asking_price
            if search_params.max_asking_price is not None:
                price_filter["$lte"] = search_params.max_asking_price
            query["financial_info.asking_price"] = price_filter
        
        # 公司規模篩選
        if search_params.company_sizes:
            query["company_info.company_size"] = {"$in": search_params.company_sizes}
        
        # 地區篩選
        if search_params.regions:
            query["company_info.headquarters"] = {"$in": search_params.regions}
        
        # 時間範圍篩選
        if search_params.created_after or search_params.created_before:
            date_filter = {}
            if search_params.created_after:
                date_filter["$gte"] = search_params.created_after
            if search_params.created_before:
                date_filter["$lte"] = search_params.created_before
            query["created_at"] = date_filter
        
        return query
    
    async def _build_sort_condition(self, search_params: ProposalSearchParams) -> List[Tuple[str, int]]:
        """建立排序條件"""
        sort_direction = -1 if search_params.sort_order == "desc" else 1
        
        # 驗證排序欄位
        allowed_sort_fields = [
            "created_at", "updated_at", "view_count", "sent_count",
            "company_info.company_name", "financial_info.annual_revenue",
            "financial_info.asking_price", "teaser_content.title"
        ]
        
        sort_field = search_params.sort_by
        if sort_field not in allowed_sort_fields:
            sort_field = "created_at"
        
        return [(sort_field, sort_direction)]
    
    # ==================== 媒合相關操作 (預留 Phase 3) ====================
    
    async def get_matching_proposals_for_buyer(
        self, 
        buyer_id: str, 
        limit: int = 10
    ) -> List[Proposal]:
        """為買方取得媒合的提案 (預留 Phase 3 實現)"""
        try:
            # 取得買方偏好
            user_collection = await self._get_user_collection()
            buyer = await user_collection.find_one({"_id": ObjectId(buyer_id)})
            
            if not buyer or buyer.get("role") != UserRole.BUYER:
                raise BusinessException(
                    message="買方不存在",
                    error_code="BUYER_NOT_FOUND"
                )
            
            # 基礎查詢條件
            query = {
                "status": ProposalStatus.AVAILABLE,
                "is_active": True
            }
            
            # 根據買方偏好添加篩選條件
            buyer_profile = buyer.get("buyer_profile", {})
            public_profile = buyer_profile.get("public_profile", {})
            
            # 偏好行業篩選
            preferred_industries = public_profile.get("preferred_industries", [])
            if preferred_industries:
                query["company_info.industry"] = {"$in": preferred_industries}
            
            # 投資範圍篩選
            investment_range = public_profile.get("investment_range", {})
            if investment_range:
                price_filter = {}
                if "min_amount" in investment_range:
                    price_filter["$gte"] = investment_range["min_amount"]
                if "max_amount" in investment_range:
                    price_filter["$lte"] = investment_range["max_amount"]
                if price_filter:
                    query["financial_info.asking_price"] = price_filter
            
            # 地理偏好篩選
            geographic_focus = public_profile.get("geographic_focus", [])
            if geographic_focus:
                query["company_info.headquarters"] = {"$in": geographic_focus}
            
            # 執行查詢
            collection = await self._get_collection()
            cursor = collection.find(query).sort("created_at", -1).limit(limit)
            proposals_data = await cursor.to_list(length=limit)
            
            # 轉換為 Proposal 物件
            proposals = []
            for proposal_data in proposals_data:
                proposal = Proposal(**proposal_data)
                proposals.append(proposal)
            
            return proposals
            
        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            raise BusinessException(
                message=f"取得媒合提案時發生錯誤: {str(e)}",
                error_code="MATCHING_PROPOSALS_ERROR"
            )
    
    async def send_proposal_to_buyer(
        self, 
        proposal_id: str, 
        buyer_id: str, 
        sender_id: str
    ) -> bool:
        """發送提案給買方 (預留 Phase 3 實現)"""
        try:
            # 驗證提案存在且可發送
            proposal = await self._get_proposal_by_id_raw(proposal_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在",
                    error_code="PROPOSAL_NOT_FOUND"
                )
            
            if not proposal.can_send():
                raise PermissionException(
                    message=f"提案狀態為 {proposal.status}，無法發送",
                    error_code="PROPOSAL_NOT_SENDABLE"
                )
            
            # 驗證買方存在
            user_collection = await self._get_user_collection()
            buyer = await user_collection.find_one({"_id": ObjectId(buyer_id)})
            if not buyer or buyer.get("role") != UserRole.BUYER:
                raise BusinessException(
                    message="買方不存在",
                    error_code="BUYER_NOT_FOUND"
                )
            
            # 驗證發送者權限 (提案創建者或管理員)
            if str(proposal.creator_id) != sender_id:
                sender = await user_collection.find_one({"_id": ObjectId(sender_id)})
                if not sender or sender.get("role") != UserRole.ADMIN:
                    raise PermissionException(
                        message="無權限發送此提案",
                        error_code="INSUFFICIENT_PERMISSION"
                    )
            
            # 這裡應該創建 ProposalCase 記錄 (Phase 3 實現)
            # 目前只更新發送統計
            collection = await self._get_collection()
            await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$inc": {"sent_count": 1},
                    "$set": {
                        "status": ProposalStatus.SENT,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"發送提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_SEND_ERROR"
            )
    
    # ==================== 檔案管理操作 (預留) ====================
    
    async def add_proposal_file(
        self, 
        proposal_id: str, 
        user_id: str, 
        file_info: Dict[str, Any]
    ) -> bool:
        """添加提案附件 (預留實現)"""
        try:
            # 驗證提案存在且用戶有權限
            proposal = await self._get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在或無權限",
                    error_code="PROPOSAL_NOT_FOUND_OR_NO_PERMISSION"
                )
            
            # 檢查是否可以編輯
            if not proposal.can_edit():
                raise PermissionException(
                    message=f"提案狀態為 {proposal.status}，無法添加檔案",
                    error_code="PROPOSAL_NOT_EDITABLE"
                )
            
            # 創建檔案記錄
            from app.models.proposal import AttachedFile
            attached_file = AttachedFile(
                filename=file_info["filename"],
                file_type=file_info["file_type"],
                file_size=file_info["file_size"],
                file_path=file_info["file_path"],
                is_public=file_info.get("is_public", False),
                description=file_info.get("description"),
                upload_time=datetime.utcnow()
            )
            
            # 更新提案
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$push": {"attached_files": attached_file.dict()},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
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
        """移除提案附件 (預留實現)"""
        try:
            # 驗證提案存在且用戶有權限
            proposal = await self._get_proposal_for_edit(proposal_id, user_id)
            if not proposal:
                raise BusinessException(
                    message="提案不存在或無權限",
                    error_code="PROPOSAL_NOT_FOUND_OR_NO_PERMISSION"
                )
            
            # 檢查是否可以編輯
            if not proposal.can_edit():
                raise PermissionException(
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
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"移除檔案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_FILE_REMOVE_ERROR"
            )
    
    # ==================== 資料轉換輔助方法 ====================
    
    async def get_proposal_public_info(self, proposal: Proposal) -> Dict[str, Any]:
        """取得提案公開資訊 (買方可見)"""
        return {
            "id": str(proposal.id),
            "industry": proposal.company_info.industry,
            "company_size": proposal.company_info.company_size,
            "headquarters": proposal.company_info.headquarters,
            "established_year": proposal.company_info.established_year,
            "teaser_content": proposal.teaser_content.dict(),
            "view_count": proposal.view_count,
            "created_at": proposal.created_at
        }
    
    async def get_proposal_full_info(self, proposal: Proposal) -> Dict[str, Any]:
        """取得提案完整資訊 (NDA 後可見)"""
        full_info = proposal.to_dict()
        
        # 轉換 ObjectId 為字串
        full_info["_id"] = str(full_info["_id"])
        full_info["creator_id"] = str(full_info["creator_id"])
        
        # 處理審核記錄中的 ObjectId
        for record in full_info.get("review_records", []):
            if "reviewer_id" in record:
                record["reviewer_id"] = str(record["reviewer_id"])
        
        # 處理附件中的 ObjectId
        for file_info in full_info.get("attached_files", []):
            if "file_id" in file_info:
                file_info["file_id"] = str(file_info["file_id"])
        
        return full_info
    
    # ==================== 批次操作 (管理員用) ====================
    
    async def batch_approve_proposals(
        self, 
        proposal_ids: List[str], 
        reviewer_id: str, 
        reviewer_name: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """批次核准提案 (管理員用)"""
        try:
            results = {
                "success_count": 0,
                "failed_count": 0,
                "failed_proposals": []
            }
            
            for proposal_id in proposal_ids:
                try:
                    approve_request = ProposalApproveRequest(comment=comment)
                    success = await self.approve_proposal(
                        proposal_id, reviewer_id, reviewer_name, approve_request
                    )
                    
                    if success:
                        results["success_count"] += 1
                    else:
                        results["failed_count"] += 1
                        results["failed_proposals"].append({
                            "proposal_id": proposal_id,
                            "reason": "核准操作失敗"
                        })
                        
                except Exception as e:
                    results["failed_count"] += 1
                    results["failed_proposals"].append({
                        "proposal_id": proposal_id,
                        "reason": str(e)
                    })
            
            return results
            
        except Exception as e:
            raise BusinessException(
                message=f"批次核准提案時發生錯誤: {str(e)}",
                error_code="BATCH_APPROVE_ERROR"
            )
    
    async def batch_publish_proposals(self, proposal_ids: List[str]) -> Dict[str, Any]:
        """批次發布提案 (管理員用)"""
        try:
            results = {
                "success_count": 0,
                "failed_count": 0,
                "failed_proposals": []
            }
            
            for proposal_id in proposal_ids:
                try:
                    success = await self.publish_proposal(proposal_id)
                    
                    if success:
                        results["success_count"] += 1
                    else:
                        results["failed_count"] += 1
                        results["failed_proposals"].append({
                            "proposal_id": proposal_id,
                            "reason": "發布操作失敗"
                        })
                        
                except Exception as e:
                    results["failed_count"] += 1
                    results["failed_proposals"].append({
                        "proposal_id": proposal_id,
                        "reason": str(e)
                    })
            
            return results
            
        except Exception as e:
            raise BusinessException(
                message=f"批次發布提案時發生錯誤: {str(e)}",
                error_code="BATCH_PUBLISH_ERROR"
            )
    
    # ==================== 資料驗證輔助方法 ====================
    
    async def validate_proposal_data(self, proposal_data: ProposalCreate) -> List[str]:
        """驗證提案資料完整性"""
        errors = []
        
        try:
            # 驗證公司名稱唯一性 (同一創建者)
            # 這個驗證在實際創建時進行，這裡只是示例
            
            # 驗證財務數據合理性
            financial = proposal_data.financial_info
            if financial.net_profit > financial.annual_revenue:
                errors.append("淨利潤不能超過年營收")
            
            if financial.asking_price < financial.annual_revenue * 0.5:
                errors.append("要價可能過低，建議至少為年營收的 50%")
            
            # 驗證成長率合理性
            if financial.growth_rate > 200:
                errors.append("成長率超過 200% 可能不太合理，請確認數據")
            
            # 驗證員工數量與營收的合理性
            company = proposal_data.company_info
            revenue_per_employee = financial.annual_revenue / company.employee_count
            if revenue_per_employee > 10000000:  # 每員工年產值超過 1000 萬
                errors.append("每員工年產值異常高，請確認數據")
            
            # 驗證亮點數量
            if len(proposal_data.teaser_content.highlights) < 3:
                errors.append("至少需要 3 個核心亮點")
            
        except Exception as e:
            errors.append(f"資料驗證時發生錯誤: {str(e)}")
        
        return errors
    
    async def check_duplicate_company_name(
        self, 
        creator_id: str, 
        company_name: str, 
        exclude_proposal_id: Optional[str] = None
    ) -> bool:
        """檢查公司名稱是否重複 (同一創建者)"""
        try:
            collection = await self._get_collection()
            
            query = {
                "creator_id": ObjectId(creator_id),
                "company_info.company_name": company_name,
                "is_active": True
            }
            
            if exclude_proposal_id:
                query["_id"] = {"$ne": ObjectId(exclude_proposal_id)}
            
            existing = await collection.find_one(query)
            return existing is not None
            
        except Exception:
            return False