"""
提案核心服務 - ProposalCoreService
負責提案的基礎 CRUD 操作
對應 API 模組: proposals.core
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.database import Database
from app.core.exceptions import BusinessException, ValidationException, PermissionDeniedException
from app.schemas.proposal import ProposalCreate, ProposalUpdate


class ProposalCoreService:
    """提案核心服務類"""
    
    def __init__(self):
        self.database = None
        # 導入其他服務（避免循環導入）
        self.validation = None
    
    async def _get_database(self):
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
    
    def set_validation_service(self, validation_service):
        """設置驗證服務（避免循環導入）"""
        self.validation = validation_service
    
    # ==================== 基礎 CRUD 操作 ====================
    
    async def create_proposal(self, creator_id: str, proposal_data: ProposalCreate) -> Dict[str, Any]:
        """創建提案"""
        try:
            # 驗證創建者權限
            if self.validation:
                await self.validation.check_creator_permission(creator_id)
            
            # 處理公司資訊，自動計算 company_size
            company_info_dict = proposal_data.company_info.dict()
            
            # 如果沒有提供 company_size，根據員工數量自動計算
            if 'company_size' not in company_info_dict or company_info_dict['company_size'] is None:
                employee_count = company_info_dict.get('employee_count', 0)
                
                if employee_count <= 4:
                    company_info_dict['company_size'] = "微型企業"
                elif employee_count <= 29:
                    company_info_dict['company_size'] = "小型企業"
                elif employee_count <= 199:
                    company_info_dict['company_size'] = "中型企業"
                elif employee_count <= 999:
                    company_info_dict['company_size'] = "大型企業"
                else:
                    company_info_dict['company_size'] = "超大型企業"
            
            # 處理財務資訊，自動計算 profit_margin
            financial_info_dict = proposal_data.financial_info.dict()
            
            # 如果沒有提供 profit_margin，自動計算
            if 'profit_margin' not in financial_info_dict or financial_info_dict['profit_margin'] is None:
                annual_revenue = financial_info_dict.get('annual_revenue', 1)
                net_profit = financial_info_dict.get('net_profit', 0)
                if annual_revenue > 0:
                    profit_margin = (net_profit / annual_revenue) * 100
                    financial_info_dict['profit_margin'] = round(profit_margin, 2)
                else:
                    financial_info_dict['profit_margin'] = 0.0
            
            # 使用字典直接創建，而不是使用 Proposal() 構造函數
            proposal_dict = {
                "creator_id": ObjectId(creator_id),
                "company_info": company_info_dict,
                "financial_info": financial_info_dict,
                "business_model": proposal_data.business_model.dict(),
                "teaser_content": proposal_data.teaser_content.dict(),
                "status": "draft",
                "version": 1,
                "is_active": True,
                "view_count": 0,
                "sent_count": 0,
                "interest_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 如果有完整內容，添加進去
            if proposal_data.full_content:
                proposal_dict["full_content"] = proposal_data.full_content.dict()
            
            # 儲存到資料庫
            collection = await self._get_collection()
            result = await collection.insert_one(proposal_dict)
            
            if not result.inserted_id:
                raise BusinessException("提案創建失敗")
            
            # 返回創建的提案
            proposal_dict["_id"] = result.inserted_id
            return proposal_dict
            
        except Exception as e:
            raise BusinessException(f"創建提案時發生錯誤: {str(e)}")
    
    async def get_proposal_by_id(
        self, 
        proposal_id: str, 
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """根據ID取得提案"""
        try:
            collection = await self._get_collection()
            
            # 檢查 ObjectId 格式
            if not ObjectId.is_valid(proposal_id):
                raise ValidationException("提案ID格式無效")
            
            # 查詢提案
            proposal = await collection.find_one({"_id": ObjectId(proposal_id)})
            
            if not proposal:
                return None
            
            # 檢查查看權限
            if self.validation and user_id:
                await self.validation.check_view_permission(proposal, user_id)
            
            # 增加瀏覽量（如果不是創建者）
            if user_id and str(proposal.get("creator_id")) != user_id:
                await self.increment_view_count(proposal_id)
                proposal["view_count"] = proposal.get("view_count", 0) + 1
            
            return proposal
            
        except Exception as e:
            raise BusinessException(f"取得提案失敗: {str(e)}")
    
    async def update_proposal(
        self, 
        proposal_id: str, 
        user_id: str, 
        update_data: ProposalUpdate
    ) -> Dict[str, Any]:
        """更新提案"""
        try:
            collection = await self._get_collection()
            
            # 檢查提案是否存在
            proposal = await collection.find_one({"_id": ObjectId(proposal_id)})
            if not proposal:
                raise ValidationException("提案不存在")
            
            # 檢查編輯權限
            if self.validation:
                await self.validation.check_edit_permission(proposal, user_id)
            
            # 準備更新資料
            update_dict = {}
            
            if update_data.company_info:
                company_info_dict = update_data.company_info.dict()
                # 自動計算 company_size
                if 'company_size' not in company_info_dict or company_info_dict['company_size'] is None:
                    employee_count = company_info_dict.get('employee_count', 0)
                    if employee_count <= 4:
                        company_info_dict['company_size'] = "微型企業"
                    elif employee_count <= 29:
                        company_info_dict['company_size'] = "小型企業"
                    elif employee_count <= 199:
                        company_info_dict['company_size'] = "中型企業"
                    elif employee_count <= 999:
                        company_info_dict['company_size'] = "大型企業"
                    else:
                        company_info_dict['company_size'] = "超大型企業"
                update_dict["company_info"] = company_info_dict
            
            if update_data.financial_info:
                financial_info_dict = update_data.financial_info.dict()
                # 自動計算 profit_margin
                if 'profit_margin' not in financial_info_dict or financial_info_dict['profit_margin'] is None:
                    annual_revenue = financial_info_dict.get('annual_revenue', 1)
                    net_profit = financial_info_dict.get('net_profit', 0)
                    if annual_revenue > 0:
                        profit_margin = (net_profit / annual_revenue) * 100
                        financial_info_dict['profit_margin'] = round(profit_margin, 2)
                    else:
                        financial_info_dict['profit_margin'] = 0.0
                update_dict["financial_info"] = financial_info_dict
            
            if update_data.business_model:
                update_dict["business_model"] = update_data.business_model.dict()
            
            if update_data.teaser_content:
                update_dict["teaser_content"] = update_data.teaser_content.dict()
            
            if update_data.full_content:
                update_dict["full_content"] = update_data.full_content.dict()
            
            # 更新時間戳
            update_dict["updated_at"] = datetime.utcnow()
            update_dict["version"] = proposal.get("version", 1) + 1
            
            # 執行更新
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count == 0:
                raise BusinessException("提案更新失敗")
            
            # 返回更新後的提案
            updated_proposal = await collection.find_one({"_id": ObjectId(proposal_id)})
            return updated_proposal
            
        except Exception as e:
            raise BusinessException(f"更新提案失敗: {str(e)}")
    
    async def delete_proposal(self, proposal_id: str, user_id: str) -> bool:
        """刪除提案（軟刪除）"""
        try:
            collection = await self._get_collection()
            
            # 檢查提案是否存在
            proposal = await collection.find_one({"_id": ObjectId(proposal_id)})
            if not proposal:
                raise ValidationException("提案不存在")
            
            # 檢查刪除權限
            if self.validation:
                await self.validation.check_delete_permission(proposal, user_id)
            
            # 軟刪除
            result = await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {
                    "$set": {
                        "is_active": False,
                        "deleted_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise BusinessException(f"刪除提案失敗: {str(e)}")
    
    async def get_proposals_by_creator(
        self, 
        creator_id: str, 
        skip: int = 0, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """取得創建者的提案列表"""
        try:
            collection = await self._get_collection()
            
            # 查詢條件
            query = {
                "creator_id": ObjectId(creator_id),
                "is_active": True
            }
            
            # 取得總數
            total = await collection.count_documents(query)
            
            # 取得提案列表
            cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            proposals = await cursor.to_list(length=limit)
            
            return {
                "proposals": proposals,
                "total": total,
                "skip": skip,
                "limit": limit
            }
            
        except Exception as e:
            raise BusinessException(f"取得創建者提案失敗: {str(e)}")
    
    async def get_proposal_for_edit(self, proposal_id: str, user_id: str) -> Dict[str, Any]:
        """取得提案編輯資訊"""
        try:
            proposal = await self.get_proposal_by_id(proposal_id, user_id)
            
            if not proposal:
                raise ValidationException("提案不存在")
            
            # 檢查編輯權限
            if self.validation:
                await self.validation.check_edit_permission(proposal, user_id)
            
            return proposal
            
        except Exception as e:
            raise BusinessException(f"取得編輯權限失敗: {str(e)}")
    
    async def get_proposal_statistics(self, proposal_id: str, user_id: str) -> Dict[str, Any]:
        """取得提案統計資訊"""
        try:
            proposal = await self.get_proposal_by_id(proposal_id, user_id)
            
            if not proposal:
                raise ValidationException("提案不存在")
            
            # 檢查查看權限
            if self.validation:
                await self.validation.check_view_permission(proposal, user_id)
            
            # 統計資訊
            stats = {
                "view_count": proposal.get("view_count", 0),
                "sent_count": proposal.get("sent_count", 0),
                "interest_count": proposal.get("interest_count", 0),
                "created_at": proposal.get("created_at"),
                "updated_at": proposal.get("updated_at"),
                "status": proposal.get("status"),
                "version": proposal.get("version", 1)
            }
            
            return stats
            
        except Exception as e:
            raise BusinessException(f"取得提案統計失敗: {str(e)}")
    
    # ==================== 輔助方法 ====================
    
    async def increment_view_count(self, proposal_id: str):
        """增加瀏覽量"""
        try:
            collection = await self._get_collection()
            await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {"$inc": {"view_count": 1}}
            )
        except Exception:
            # 瀏覽量更新失敗不影響主要功能
            pass
    
    async def increment_sent_count(self, proposal_id: str):
        """增加發送次數"""
        try:
            collection = await self._get_collection()
            await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {"$inc": {"sent_count": 1}}
            )
        except Exception:
            pass
    
    async def increment_interest_count(self, proposal_id: str):
        """增加感興趣次數"""
        try:
            collection = await self._get_collection()
            await collection.update_one(
                {"_id": ObjectId(proposal_id)},
                {"$inc": {"interest_count": 1}}
            )
        except Exception:
            pass