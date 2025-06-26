"""
提案驗證服務 - Validation Service
負責提案相關的所有資料驗證和權限檢查
這是其他服務模組的基礎依賴，確保資料的完整性和安全性
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.core.database import Database
from app.core.exceptions import ValidationException, PermissionDeniedException, BusinessException
from app.models.proposal import Proposal, ProposalStatus, Industry, CompanySize
from app.models.user import UserRole
from app.schemas.proposal import ProposalCreate, ProposalUpdate


class ProposalValidationService:
    """提案驗證服務類 - 資料驗證和權限檢查"""
    
    def __init__(self):
        """初始化驗證服務"""
        self.database = None
        
    async def _get_database(self) -> AsyncIOMotorDatabase:
        """取得資料庫實例"""
        if self.database is None:
            self.database = Database.get_database()
        return self.database
    
    async def _get_user_collection(self) -> AsyncIOMotorCollection:
        """取得用戶集合"""
        database = await self._get_database()
        return database.users
    
    async def _get_proposal_collection(self) -> AsyncIOMotorCollection:
        """取得提案集合"""
        database = await self._get_database()
        return database.proposals
    
    # ==================== 權限驗證 ====================
    
    async def check_creator_permission(self, user_id: str) -> None:
        """
        檢查用戶是否有創建提案的權限
        
        Args:
            user_id: 用戶 ID
            
        Raises:
            PermissionDeniedException: 權限不足
            ValidationException: 用戶不存在
        """
        try:
            user_collection = await self._get_user_collection()
            user = await user_collection.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                raise ValidationException(
                    message="用戶不存在",
                    error_code="USER_NOT_FOUND"
                )
            
            # 檢查用戶角色
            user_role = user.get("role")
            if user_role not in [UserRole.SELLER, UserRole.ADMIN]:
                raise PermissionDeniedException(
                    message="只有提案方和管理員可以創建提案",
                    error_code="PROPOSAL_CREATE_NO_PERMISSION"
                )
            
            # 檢查用戶狀態
            if not user.get("is_active", True):
                raise PermissionDeniedException(
                    message="用戶帳號已被禁用",
                    error_code="USER_ACCOUNT_DISABLED"
                )
                
        except Exception as e:
            if isinstance(e, (PermissionDeniedException, ValidationException)):
                raise
            raise ValidationException(
                message=f"檢查創建權限時發生錯誤: {str(e)}",
                error_code="PERMISSION_CHECK_ERROR"
            )
    
    async def check_view_permission(
        self, 
        proposal: Proposal, 
        user_id: str
    ) -> Dict[str, bool]:
        """
        檢查用戶對提案的查看權限
        
        Args:
            proposal: 提案實例
            user_id: 用戶 ID
            
        Returns:
            Dict[str, bool]: 權限字典
                - can_view_teaser: 可以查看 Teaser
                - can_view_full: 可以查看完整內容
                - can_edit: 可以編輯
                - can_delete: 可以刪除
        """
        try:
            user_collection = await self._get_user_collection()
            user = await user_collection.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                return {
                    "can_view_teaser": False,
                    "can_view_full": False,
                    "can_edit": False,
                    "can_delete": False
                }
            
            user_role = user.get("role")
            is_creator = str(proposal.creator_id) == user_id
            is_admin = user_role == UserRole.ADMIN
            
            # 基本查看權限
            can_view_teaser = (
                proposal.status in [ProposalStatus.AVAILABLE, ProposalStatus.SENT] or
                is_creator or 
                is_admin
            )
            
            # 完整內容查看權限 (需要 NDA 或創建者/管理員)
            can_view_full = (
                is_creator or 
                is_admin or
                self._has_nda_access(proposal, user_id)  # TODO: 實現 NDA 檢查
            )
            
            # 編輯權限
            can_edit = (
                (is_creator and proposal.can_edit()) or
                is_admin
            )
            
            # 刪除權限
            can_delete = (
                (is_creator and proposal.status in [ProposalStatus.DRAFT, ProposalStatus.REJECTED]) or
                is_admin
            )
            
            return {
                "can_view_teaser": can_view_teaser,
                "can_view_full": can_view_full,
                "can_edit": can_edit,
                "can_delete": can_delete
            }
            
        except Exception as e:
            # 權限檢查失敗時，預設為無權限
            return {
                "can_view_teaser": False,
                "can_view_full": False,
                "can_edit": False,
                "can_delete": False
            }
    
    async def check_admin_permission(self, user_id: str) -> None:
        """
        檢查用戶是否有管理員權限
        
        Args:
            user_id: 用戶 ID
            
        Raises:
            PermissionDeniedException: 非管理員
        """
        try:
            user_collection = await self._get_user_collection()
            user = await user_collection.find_one({"_id": ObjectId(user_id)})
            
            if not user or user.get("role") != UserRole.ADMIN:
                raise PermissionDeniedException(
                    message="需要管理員權限",
                    error_code="ADMIN_PERMISSION_REQUIRED"
                )
            
            if not user.get("is_active", True):
                raise PermissionDeniedException(
                    message="管理員帳號已被禁用",
                    error_code="ADMIN_ACCOUNT_DISABLED"
                )
                
        except Exception as e:
            if isinstance(e, PermissionDeniedException):
                raise
            raise PermissionDeniedException(
                message=f"檢查管理員權限時發生錯誤: {str(e)}",
                error_code="ADMIN_PERMISSION_CHECK_ERROR"
            )
    
    # ==================== 資料驗證 ====================
    
    async def validate_proposal_data(self, proposal_data: ProposalCreate) -> None:
        """
        驗證提案創建資料的完整性和有效性
        
        Args:
            proposal_data: 提案創建資料
            
        Raises:
            ValidationException: 資料驗證失敗
        """
        try:
            # 驗證公司基本資訊
            await self._validate_company_info(proposal_data.company_info)
            
            # 驗證財務資訊
            await self._validate_financial_info(proposal_data.financial_info)
            
            # 驗證商業模式
            await self._validate_business_model(proposal_data.business_model)
            
            # 驗證 Teaser 內容
            await self._validate_teaser_content(proposal_data.teaser_content)
            
            # 驗證完整內容 (如果提供)
            if proposal_data.full_content:
                await self._validate_full_content(proposal_data.full_content)
                
        except Exception as e:
            if isinstance(e, ValidationException):
                raise
            raise ValidationException(
                message=f"提案資料驗證失敗: {str(e)}",
                error_code="PROPOSAL_DATA_VALIDATION_ERROR"
            )
    
    async def validate_proposal_update(
        self, 
        proposal: Proposal, 
        update_data: ProposalUpdate
    ) -> None:
        """
        驗證提案更新資料
        
        Args:
            proposal: 現有提案實例
            update_data: 更新資料
            
        Raises:
            ValidationException: 更新資料無效
            BusinessException: 業務規則違反
        """
        try:
            # 檢查提案狀態是否允許更新
            if not proposal.can_edit():
                raise BusinessException(
                    message=f"提案狀態為 {proposal.status}，無法編輯",
                    error_code="PROPOSAL_NOT_EDITABLE"
                )
            
            # 驗證各個更新區塊
            if update_data.company_info:
                await self._validate_company_info(update_data.company_info)
            
            if update_data.financial_info:
                await self._validate_financial_info(update_data.financial_info)
            
            if update_data.business_model:
                await self._validate_business_model(update_data.business_model)
            
            if update_data.teaser_content:
                await self._validate_teaser_content(update_data.teaser_content)
            
            if update_data.full_content:
                await self._validate_full_content(update_data.full_content)
                
        except Exception as e:
            if isinstance(e, (ValidationException, BusinessException)):
                raise
            raise ValidationException(
                message=f"提案更新驗證失敗: {str(e)}",
                error_code="PROPOSAL_UPDATE_VALIDATION_ERROR"
            )
    
    async def validate_status_transition(
        self, 
        current_status: ProposalStatus, 
        target_status: ProposalStatus
    ) -> None:
        """
        驗證提案狀態轉換是否合法
        
        Args:
            current_status: 當前狀態
            target_status: 目標狀態
            
        Raises:
            ValidationException: 狀態轉換不合法
        """
        # 定義合法的狀態轉換
        valid_transitions = {
            ProposalStatus.DRAFT: [ProposalStatus.UNDER_REVIEW, ProposalStatus.ARCHIVED],
            ProposalStatus.UNDER_REVIEW: [ProposalStatus.APPROVED, ProposalStatus.REJECTED, ProposalStatus.DRAFT],
            ProposalStatus.APPROVED: [ProposalStatus.AVAILABLE, ProposalStatus.ARCHIVED],
            ProposalStatus.AVAILABLE: [ProposalStatus.SENT, ProposalStatus.ARCHIVED],
            ProposalStatus.SENT: [ProposalStatus.ARCHIVED],
            ProposalStatus.REJECTED: [ProposalStatus.DRAFT, ProposalStatus.ARCHIVED],
            ProposalStatus.ARCHIVED: []  # 歸檔後不能轉換
        }
        
        if target_status not in valid_transitions.get(current_status, []):
            raise ValidationException(
                message=f"無法從 {current_status} 轉換到 {target_status}",
                error_code="INVALID_STATUS_TRANSITION"
            )
    
    # ==================== 業務規則驗證 ====================
    
    async def validate_business_rules(self, proposal_data: Any) -> None:
        """
        驗證業務規則
        
        Args:
            proposal_data: 提案相關資料
            
        Raises:
            ValidationException: 業務規則驗證失敗
        """
        # 檢查提案數量限制 (每個用戶最多同時有 10 個草稿)
        # 檢查公司名稱唯一性
        # 檢查財務資料合理性
        # 其他業務規則...
        pass
    
    async def check_data_completeness(self, proposal: Proposal) -> Dict[str, Any]:
        """
        檢查提案資料完整性
        
        Args:
            proposal: 提案實例
            
        Returns:
            Dict[str, Any]: 完整性報告
        """
        completeness = {
            "overall_score": 0,
            "missing_fields": [],
            "suggestions": [],
            "ready_for_submission": False
        }
        
        # 檢查必要欄位
        required_fields = [
            "company_info.company_name",
            "company_info.industry", 
            "company_info.established_year",
            "financial_info.revenue",
            "teaser_content.business_overview"
        ]
        
        # 計算完整性分數
        # 添加改進建議
        # 判斷是否可以提交
        
        return completeness
    
    # ==================== 私有驗證方法 ====================
    
    async def _validate_company_info(self, company_info) -> None:
        """驗證公司資訊"""
        if not company_info.company_name or len(company_info.company_name.strip()) < 2:
            raise ValidationException(
                message="公司名稱至少需要 2 個字元",
                error_code="COMPANY_NAME_TOO_SHORT"
            )
        
        if company_info.industry not in Industry:
            raise ValidationException(
                message="無效的行業分類",
                error_code="INVALID_INDUSTRY"
            )
        
        current_year = datetime.now().year
        if company_info.established_year < 1900 or company_info.established_year > current_year:
            raise ValidationException(
                message=f"成立年份必須在 1900 到 {current_year} 之間",
                error_code="INVALID_ESTABLISHED_YEAR"
            )
    
    async def _validate_financial_info(self, financial_info) -> None:
        """驗證財務資訊"""
        if financial_info.revenue is not None and financial_info.revenue < 0:
            raise ValidationException(
                message="營收不能為負數",
                error_code="NEGATIVE_REVENUE"
            )
        
        if financial_info.profit is not None and financial_info.revenue is not None:
            if abs(financial_info.profit) > financial_info.revenue * 2:
                raise ValidationException(
                    message="利潤數據可能不合理",
                    error_code="UNREALISTIC_PROFIT"
                )
    
    async def _validate_business_model(self, business_model) -> None:
        """驗證商業模式"""
        if business_model.revenue_streams and len(business_model.revenue_streams) == 0:
            raise ValidationException(
                message="至少需要一個收入來源",
                error_code="NO_REVENUE_STREAMS"
            )
    
    async def _validate_teaser_content(self, teaser_content) -> None:
        """驗證 Teaser 內容"""
        if not teaser_content.business_overview or len(teaser_content.business_overview.strip()) < 50:
            raise ValidationException(
                message="業務概述至少需要 50 個字元",
                error_code="BUSINESS_OVERVIEW_TOO_SHORT"
            )
    
    async def _validate_full_content(self, full_content) -> None:
        """驗證完整內容"""
        if not full_content.detailed_description or len(full_content.detailed_description.strip()) < 200:
            raise ValidationException(
                message="詳細描述至少需要 200 個字元",
                error_code="DETAILED_DESCRIPTION_TOO_SHORT"
            )
    
    def _has_nda_access(self, proposal: Proposal, user_id: str) -> bool:
        """
        檢查用戶是否有 NDA 存取權限
        
        TODO: Phase 3 實現 NDA 系統後完整實現此方法
        
        Args:
            proposal: 提案實例
            user_id: 用戶 ID
            
        Returns:
            bool: 是否有 NDA 存取權限
        """
        # 暫時返回 False，Phase 3 實現 NDA 系統後完整實現
        return False