"""
提案服務模組統一入口 - __init__.py
整合所有模組化的提案服務，提供統一的服務接口
"""

from .validation_service import ProposalValidationService
from .core_service import ProposalCoreService
from .workflow_service import ProposalWorkflowService
from .search_service import ProposalSearchService
from .admin_service import ProposalAdminService


class ProposalService:
    """
    提案管理主服務類
    整合所有子服務模組，提供統一的服務接口
    """
    
    def __init__(self):
        # 初始化所有子服務
        self.validation = ProposalValidationService()
        self.core = ProposalCoreService()
        self.workflow = ProposalWorkflowService()
        self.search = ProposalSearchService()
        self.admin = ProposalAdminService()
        
        # 設置服務間的依賴關係（避免循環導入）
        self._setup_service_dependencies()
    
    def _setup_service_dependencies(self):
        """設置服務間的依賴關係"""
        # core_service 需要 validation_service
        self.core.set_validation_service(self.validation)
        
        # workflow_service 需要 core_service 和 validation_service
        if hasattr(self.workflow, 'set_core_service'):
            self.workflow.set_core_service(self.core)
        if hasattr(self.workflow, 'set_validation_service'):
            self.workflow.set_validation_service(self.validation)
        
        # admin_service 需要其他服務
        if hasattr(self.admin, 'set_core_service'):
            self.admin.set_core_service(self.core)
        if hasattr(self.admin, 'set_workflow_service'):
            self.admin.set_workflow_service(self.workflow)
        if hasattr(self.admin, 'set_validation_service'):
            self.admin.set_validation_service(self.validation)
    
    # ==================== 核心 CRUD 操作代理方法 ====================
    
    async def create_proposal(self, creator_id: str, proposal_data):
        """創建提案（代理到 core_service）"""
        return await self.core.create_proposal(creator_id, proposal_data)
    
    async def get_proposal_by_id(self, proposal_id: str, user_id: str = None):
        """取得提案詳情（代理到 core_service）"""
        return await self.core.get_proposal_by_id(proposal_id, user_id)
    
    async def update_proposal(self, proposal_id: str, user_id: str, update_data):
        """更新提案（代理到 core_service）"""
        return await self.core.update_proposal(proposal_id, user_id, update_data)
    
    async def delete_proposal(self, proposal_id: str, user_id: str):
        """刪除提案（代理到 core_service）"""
        return await self.core.delete_proposal(proposal_id, user_id)
    
    async def get_proposals_by_creator(self, creator_id: str, skip: int = 0, limit: int = 10):
        """取得創建者提案列表（代理到 core_service）"""
        return await self.core.get_proposals_by_creator(creator_id, skip, limit)
    
    async def get_proposal_for_edit(self, proposal_id: str, user_id: str):
        """取得提案編輯權限（代理到 core_service）"""
        return await self.core.get_proposal_for_edit(proposal_id, user_id)
    
    async def get_proposal_statistics(self, proposal_id: str, user_id: str):
        """取得提案統計（代理到 core_service）"""
        return await self.core.get_proposal_statistics(proposal_id, user_id)
    
    # ==================== 工作流程操作代理方法 ====================
    
    async def submit_proposal(self, proposal_id: str, user_id: str, submit_data):
        """提交提案審核（代理到 workflow_service）"""
        return await self.workflow.submit_proposal(proposal_id, user_id, submit_data)
    
    async def withdraw_proposal(self, proposal_id: str, user_id: str):
        """撤回提案（代理到 workflow_service）"""
        return await self.workflow.withdraw_proposal(proposal_id, user_id)
    
    async def publish_proposal(self, proposal_id: str, user_id: str):
        """發布提案（代理到 workflow_service）"""
        return await self.workflow.publish_proposal(proposal_id, user_id)
    
    async def archive_proposal(self, proposal_id: str, user_id: str):
        """歸檔提案（代理到 workflow_service）"""
        return await self.workflow.archive_proposal(proposal_id, user_id)
    
    # ==================== 搜尋操作代理方法 ====================
    
    async def search_proposals(self, search_params, user_id: str = None):
        """搜尋提案（代理到 search_service）"""
        return await self.search.search_proposals(search_params, user_id)
    
    async def full_text_search(self, keyword: str, user_id: str = None):
        """全文搜尋（代理到 search_service）"""
        return await self.search.full_text_search(keyword, user_id)
    
    # ==================== 管理員操作代理方法 ====================
    
    async def approve_proposal(self, proposal_id: str, admin_id: str, approve_data):
        """審核通過提案（代理到 admin_service）"""
        return await self.admin.approve_proposal(proposal_id, admin_id, approve_data)
    
    async def reject_proposal(self, proposal_id: str, admin_id: str, reject_data):
        """審核拒絕提案（代理到 admin_service）"""
        return await self.admin.reject_proposal(proposal_id, admin_id, reject_data)
    
    async def get_pending_reviews(self, admin_id: str):
        """取得待審核提案列表（代理到 admin_service）"""
        return await self.admin.get_pending_reviews(admin_id)


# 導出主要類別和服務
__all__ = [
    "ProposalService",
    "ProposalValidationService", 
    "ProposalCoreService",
    "ProposalWorkflowService",
    "ProposalSearchService",
    "ProposalAdminService"
]

# 版本資訊
__version__ = "2.0.0"
__description__ = "M&A 平台提案管理服務 - 完整模組化架構"