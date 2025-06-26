"""
提案管理員服務 - Admin Service
負責管理員專用的提案管理功能
包括審核、批量操作、統計分析等
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.exceptions import BusinessException, PermissionException, ValidationException
from app.models.proposal import Proposal, ProposalStatus, ReviewRecord
from app.schemas.proposal import ProposalApproveRequest, ProposalRejectRequest


class ProposalAdminService:
    """提案管理員服務類 - 管理員專用功能"""
    
    def __init__(self, core_service, workflow_service, validation_service):
        """
        初始化管理員服務
        
        Args:
            core_service: 核心服務實例
            workflow_service: 工作流程服務實例
            validation_service: 驗證服務實例
        """
        self.core = core_service
        self.workflow = workflow_service
        self.validation = validation_service
    
    # ==================== 提案審核功能 ====================
    
    async def approve_proposal(
        self, 
        proposal_id: str, 
        admin_id: str, 
        approve_data: ProposalApproveRequest
    ) -> bool:
        """
        審核通過提案
        
        Args:
            proposal_id: 提案 ID
            admin_id: 管理員 ID
            approve_data: 審核通過資料
            
        Returns:
            bool: 審核是否成功
            
        Raises:
            PermissionException: 非管理員權限
            BusinessException: 提案狀態不允許審核
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
            
            # 檢查提案狀態
            if proposal.status != ProposalStatus.UNDER_REVIEW:
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法審核",
                    error_code="PROPOSAL_NOT_REVIEWABLE"
                )
            
            # 驗證狀態轉換
            await self.validation.validate_status_transition(
                proposal.status, 
                ProposalStatus.APPROVED
            )
            
            # 執行審核通過
            success = await self.workflow._transition_status(
                proposal_id=proposal_id,
                from_status=proposal.status,
                to_status=ProposalStatus.APPROVED,
                operator_id=admin_id,
                comment=approve_data.comment or "審核通過",
                metadata={
                    "approved_at": datetime.utcnow(),
                    "approved_by": admin_id,
                    "approve_data": approve_data.dict(),
                    "auto_publish": approve_data.auto_publish
                }
            )
            
            # 如果設定自動發布，則立即發布
            if success and approve_data.auto_publish:
                await self.workflow.publish_proposal(proposal_id, admin_id)
            
            if success:
                # TODO: 發送通知給創建者
                await self._notify_creator_approved(proposal_id, admin_id, approve_data)
            
            return success
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException)):
                raise
            raise BusinessException(
                message=f"審核提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_APPROVE_ERROR"
            )
    
    async def reject_proposal(
        self, 
        proposal_id: str, 
        admin_id: str, 
        reject_data: ProposalRejectRequest
    ) -> bool:
        """
        審核拒絕提案
        
        Args:
            proposal_id: 提案 ID
            admin_id: 管理員 ID
            reject_data: 審核拒絕資料
            
        Returns:
            bool: 審核是否成功
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
            
            # 檢查提案狀態
            if proposal.status != ProposalStatus.UNDER_REVIEW:
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法審核",
                    error_code="PROPOSAL_NOT_REVIEWABLE"
                )
            
            # 驗證拒絕原因
            if not reject_data.reason or len(reject_data.reason.strip()) < 10:
                raise ValidationException(
                    message="拒絕原因至少需要 10 個字元",
                    error_code="REJECT_REASON_TOO_SHORT"
                )
            
            # 驗證狀態轉換
            await self.validation.validate_status_transition(
                proposal.status, 
                ProposalStatus.REJECTED
            )
            
            # 執行審核拒絕
            success = await self.workflow._transition_status(
                proposal_id=proposal_id,
                from_status=proposal.status,
                to_status=ProposalStatus.REJECTED,
                operator_id=admin_id,
                comment=reject_data.reason,
                metadata={
                    "rejected_at": datetime.utcnow(),
                    "rejected_by": admin_id,
                    "reject_data": reject_data.dict(),
                    "improvement_suggestions": reject_data.improvement_suggestions
                }
            )
            
            if success:
                # TODO: 發送通知給創建者
                await self._notify_creator_rejected(proposal_id, admin_id, reject_data)
            
            return success
            
        except Exception as e:
            if isinstance(e, (BusinessException, PermissionException, ValidationException)):
                raise
            raise BusinessException(
                message=f"拒絕提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_REJECT_ERROR"
            )
    
    # ==================== 批量操作功能 ====================
    
    async def batch_approve(
        self, 
        proposal_ids: List[str], 
        admin_id: str,
        batch_comment: str = "批量審核通過"
    ) -> Dict[str, Any]:
        """
        批量審核通過提案
        
        Args:
            proposal_ids: 提案 ID 列表
            admin_id: 管理員 ID
            batch_comment: 批量操作註釋
            
        Returns:
            Dict[str, Any]: 批量操作結果
        """
        try:
            # 檢查管理員權限
            await self.validation.check_admin_permission(admin_id)
            
            results = {
                "total": len(proposal_ids),
                "successful": [],
                "failed": [],
                "errors": {}
            }
            
            for proposal_id in proposal_ids:
                try:
                    # 建立審核資料
                    approve_data = ProposalApproveRequest(
                        comment=batch_comment,
                        auto_publish=False  # 批量操作不自動發布
                    )
                    
                    success = await self.approve_proposal(proposal_id, admin_id, approve_data)
                    
                    if success:
                        results["successful"].append(proposal_id)
                    else:
                        results["failed"].append(proposal_id)
                        results["errors"][proposal_id] = "審核失敗"
                        
                except Exception as e:
                    results["failed"].append(proposal_id)
                    results["errors"][proposal_id] = str(e)
            
            return results
            
        except Exception as e:
            raise BusinessException(
                message=f"批量審核時發生錯誤: {str(e)}",
                error_code="BATCH_APPROVE_ERROR"
            )
    
    async def batch_reject(
        self, 
        proposal_ids: List[str], 
        admin_id: str,
        batch_reason: str
    ) -> Dict[str, Any]:
        """
        批量審核拒絕提案
        
        Args:
            proposal_ids: 提案 ID 列表
            admin_id: 管理員 ID
            batch_reason: 批量拒絕原因
            
        Returns:
            Dict[str, Any]: 批量操作結果
        """
        try:
            # 檢查管理員權限
            await self.validation.check_admin_permission(admin_id)
            
            # 驗證批量拒絕原因
            if not batch_reason or len(batch_reason.strip()) < 10:
                raise ValidationException(
                    message="批量拒絕原因至少需要 10 個字元",
                    error_code="BATCH_REJECT_REASON_TOO_SHORT"
                )
            
            results = {
                "total": len(proposal_ids),
                "successful": [],
                "failed": [],
                "errors": {}
            }
            
            for proposal_id in proposal_ids:
                try:
                    # 建立拒絕資料
                    reject_data = ProposalRejectRequest(
                        reason=batch_reason,
                        improvement_suggestions=[]
                    )
                    
                    success = await self.reject_proposal(proposal_id, admin_id, reject_data)
                    
                    if success:
                        results["successful"].append(proposal_id)
                    else:
                        results["failed"].append(proposal_id)
                        results["errors"][proposal_id] = "拒絕失敗"
                        
                except Exception as e:
                    results["failed"].append(proposal_id)
                    results["errors"][proposal_id] = str(e)
            
            return results
            
        except Exception as e:
            raise BusinessException(
                message=f"批量拒絕時發生錯誤: {str(e)}",
                error_code="BATCH_REJECT_ERROR"
            )
    
    # ==================== 審核歷史和統計 ====================
    
    async def get_review_history(
        self, 
        admin_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        取得審核歷史記錄
        
        Args:
            admin_id: 管理員 ID (可選，篩選特定管理員)
            date_from: 開始日期
            date_to: 結束日期
            page: 頁碼
            page_size: 每頁大小
            
        Returns:
            Dict[str, Any]: 審核歷史記錄和分頁資訊
        """
        try:
            collection = await self.core._get_collection()
            
            # 建構查詢條件
            match_stage = {
                "review_records": {"$exists": True, "$ne": []}
            }
            
            # 日期範圍篩選
            if date_from or date_to:
                date_filter = {}
                if date_from:
                    date_filter["$gte"] = date_from
                if date_to:
                    date_filter["$lte"] = date_to
                match_stage["review_records.created_at"] = date_filter
            
            # 聚合管道
            pipeline = [
                {"$match": match_stage},
                {"$unwind": "$review_records"},
                {"$match": {"review_records.action": {"$regex": "to_(approved|rejected)"}}},
                {
                    "$project": {
                        "proposal_id": "$_id",
                        "proposal_title": "$company_info.company_name",
                        "review_record": "$review_records",
                        "proposal_status": "$status"
                    }
                },
                {"$sort": {"review_record.created_at": -1}}
            ]
            
            # 如果指定管理員，添加篩選
            if admin_id:
                pipeline.append({
                    "$match": {"review_record.reviewer_id": ObjectId(admin_id)}
                })
            
            # 執行聚合查詢
            cursor = collection.aggregate(pipeline)
            all_records = await cursor.to_list(None)
            
            # 分頁處理
            total_count = len(all_records)
            offset = (page - 1) * page_size
            paginated_records = all_records[offset:offset + page_size]
            
            # 格式化結果
            formatted_records = []
            for record in paginated_records:
                formatted_records.append({
                    "proposal_id": str(record["proposal_id"]),
                    "proposal_title": record["proposal_title"],
                    "action": record["review_record"]["action"],
                    "status_from": record["review_record"]["status_from"],
                    "status_to": record["review_record"]["status_to"],
                    "reviewer_id": str(record["review_record"]["reviewer_id"]),
                    "comment": record["review_record"]["comment"],
                    "created_at": record["review_record"]["created_at"],
                    "current_status": record["proposal_status"]
                })
            
            return {
                "records": formatted_records,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
            
        except Exception as e:
            raise BusinessException(
                message=f"取得審核歷史時發生錯誤: {str(e)}",
                error_code="REVIEW_HISTORY_ERROR"
            )
    
    async def get_proposal_statistics(
        self, 
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        取得提案統計資訊
        
        Args:
            date_from: 開始日期
            date_to: 結束日期
            
        Returns:
            Dict[str, Any]: 統計資訊
        """
        try:
            collection = await self.core._get_collection()
            
            # 建構日期範圍查詢
            date_query = {}
            if date_from or date_to:
                date_range = {}
                if date_from:
                    date_range["$gte"] = date_from
                if date_to:
                    date_range["$lte"] = date_to
                date_query["created_at"] = date_range
            
            # 總體統計聚合
            overall_pipeline = [
                {"$match": date_query},
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "avg_view_count": {"$avg": "$view_count"}
                    }
                }
            ]
            
            overall_stats = await collection.aggregate(overall_pipeline).to_list(None)
            
            # 按狀態統計
            status_stats = {}
            total_proposals = 0
            
            for stat in overall_stats:
                status = stat["_id"]
                count = stat["count"]
                status_stats[status] = {
                    "count": count,
                    "avg_view_count": round(stat["avg_view_count"], 2)
                }
                total_proposals += count
            
            # 行業分布統計
            industry_pipeline = [
                {"$match": date_query},
                {
                    "$group": {
                        "_id": "$company_info.industry",
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            
            industry_stats = await collection.aggregate(industry_pipeline).to_list(None)
            
            # 審核效率統計
            review_pipeline = [
                {"$match": {**date_query, "review_records": {"$exists": True, "$ne": []}}},
                {"$unwind": "$review_records"},
                {
                    "$group": {
                        "_id": "$review_records.reviewer_id",
                        "review_count": {"$sum": 1},
                        "avg_review_time": {"$avg": {
                            "$subtract": ["$review_records.created_at", "$created_at"]
                        }}
                    }
                }
            ]
            
            review_stats = await collection.aggregate(review_pipeline).to_list(None)
            
            return {
                "summary": {
                    "total_proposals": total_proposals,
                    "pending_review": status_stats.get(ProposalStatus.UNDER_REVIEW, {}).get("count", 0),
                    "approved": status_stats.get(ProposalStatus.APPROVED, {}).get("count", 0),
                    "rejected": status_stats.get(ProposalStatus.REJECTED, {}).get("count", 0),
                    "available": status_stats.get(ProposalStatus.AVAILABLE, {}).get("count", 0)
                },
                "status_distribution": status_stats,
                "top_industries": [
                    {"industry": stat["_id"], "count": stat["count"]} 
                    for stat in industry_stats
                ],
                "review_efficiency": {
                    "total_reviewers": len(review_stats),
                    "avg_reviews_per_reviewer": round(
                        sum(stat["review_count"] for stat in review_stats) / len(review_stats)
                        if review_stats else 0, 2
                    )
                },
                "period": {
                    "from": date_from,
                    "to": date_to
                }
            }
            
        except Exception as e:
            raise BusinessException(
                message=f"取得統計資訊時發生錯誤: {str(e)}",
                error_code="STATISTICS_ERROR"
            )
    
    # ==================== 管理員專用查詢 ====================
    
    async def get_pending_reviews(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        取得待審核的提案列表
        
        Args:
            page: 頁碼
            page_size: 每頁大小
            
        Returns:
            Dict[str, Any]: 待審核提案列表和分頁資訊
        """
        try:
            collection = await self.core._get_collection()
            
            # 查詢待審核提案
            query = {"status": ProposalStatus.UNDER_REVIEW}
            
            # 計算總數量
            total_count = await collection.count_documents(query)
            
            # 分頁查詢
            offset = (page - 1) * page_size
            cursor = collection.find(query).sort("created_at", 1).skip(offset).limit(page_size)
            
            proposals = []
            async for proposal_dict in cursor:
                proposal = Proposal.from_dict(proposal_dict)
                
                # 計算等待審核時間
                waiting_time = datetime.utcnow() - proposal.created_at
                
                proposals.append({
                    "id": str(proposal.id),
                    "company_name": proposal.company_info.company_name,
                    "industry": proposal.company_info.industry,
                    "creator_id": str(proposal.creator_id),
                    "submitted_at": proposal.updated_at,  # 最後更新時間作為提交時間
                    "waiting_days": waiting_time.days,
                    "teaser_summary": proposal.teaser_content.business_overview[:200] + "..."
                })
            
            return {
                "proposals": proposals,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
            
        except Exception as e:
            raise BusinessException(
                message=f"取得待審核列表時發生錯誤: {str(e)}",
                error_code="PENDING_REVIEWS_ERROR"
            )
    
    # ==================== 通知功能 (預留) ====================
    
    async def _notify_creator_approved(
        self, 
        proposal_id: str, 
        admin_id: str, 
        approve_data: ProposalApproveRequest
    ):
        """通知創建者提案已通過審核 (預留實現)"""
        # TODO: 實現通知系統後完整實現
        print(f"提案審核通過通知: 提案 {proposal_id} 已通過管理員 {admin_id} 審核")
    
    async def _notify_creator_rejected(
        self, 
        proposal_id: str, 
        admin_id: str, 
        reject_data: ProposalRejectRequest
    ):
        """通知創建者提案已被拒絕 (預留實現)"""
        # TODO: 實現通知系統後完整實現
        print(f"提案審核拒絕通知: 提案 {proposal_id} 已被管理員 {admin_id} 拒絕")