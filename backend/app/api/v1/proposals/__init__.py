"""
提案 API 模組統一入口 - __init__.py
整合所有子模組的路由，提供統一的 FastAPI Router
對應 app/services/proposal/ 的模組化服務架構
"""

from fastapi import APIRouter

# 導入所有子模組
from . import core
from . import workflow
from . import search
from . import admin  
from . import testing

# 創建主路由器
router = APIRouter()

# ==================== 整合所有子模組路由 ====================

# 1. 核心 CRUD 功能 (對應 ProposalCoreService)
router.include_router(
    core.router, 
    tags=["提案核心功能"],
    responses={404: {"description": "提案不存在"}}
)

# 2. 工作流程管理 (對應 ProposalWorkflowService)  
router.include_router(
    workflow.router,
    tags=["工作流程管理"],
    responses={422: {"description": "狀態轉換無效"}}
)

# 3. 搜尋引擎功能 (對應 ProposalSearchService)
router.include_router(
    search.router,
    tags=["搜尋引擎"],
    responses={400: {"description": "搜尋參數無效"}}
)

# 4. 管理員功能 (對應 ProposalAdminService)
router.include_router(
    admin.router,
    tags=["管理員功能"],
    responses={403: {"description": "需要管理員權限"}}
)

# 5. 測試和監控功能 (對應多個服務的測試接口)
router.include_router(
    testing.router,
    tags=["測試監控"],
    responses={503: {"description": "服務不可用"}}
)

# ==================== 模組資訊 ====================

__version__ = "2.0.0"
__description__ = "M&A 平台提案管理 API - 完整模組化架構"

# 已實現的模組
IMPLEMENTED_MODULES = [
    "core",      # 核心 CRUD (7個端點) ✅
    "workflow",  # 工作流程 (7個端點) ✅
    "search",    # 搜尋引擎 (9個端點) ✅
    "admin",     # 管理員功能 (8個端點) ✅
    "testing",   # 測試監控 (6個端點) ✅
]

# 端點統計
ENDPOINT_STATISTICS = {
    "core": 7,
    "workflow": 7, 
    "search": 9,
    "admin": 8,
    "testing": 6,
    "total": 37
}

# 模組映射到服務
MODULE_SERVICE_MAPPING = {
    "core": "ProposalCoreService",
    "workflow": "ProposalWorkflowService", 
    "search": "ProposalSearchService",
    "admin": "ProposalAdminService",
    "testing": "多服務組合測試"
}

# 檔案大小統計 (預估)
FILE_SIZE_STATISTICS = {
    "core.py": "~180行",
    "workflow.py": "~170行",
    "search.py": "~190行", 
    "admin.py": "~180行",
    "testing.py": "~160行",
    "__init__.py": "~90行",
    "總計": "~970行 (原始800行功能完全保留並增強)"
}

# 架構優勢
ARCHITECTURE_BENEFITS = [
    "檔案大小控制：每個模組 < 200行",
    "功能職責清晰：每個模組對應一個服務",
    "團隊協作友好：可並行開發不同模組",
    "測試獨立性：可分模組進行單元測試",
    "維護便利性：問題定位和修復更精準",
    "擴展靈活性：新功能可獨立模組開發"
]

# 導出主路由器和模組資訊
__all__ = [
    "router",
    "__version__", 
    "__description__",
    "IMPLEMENTED_MODULES",
    "ENDPOINT_STATISTICS", 
    "MODULE_SERVICE_MAPPING",
    "FILE_SIZE_STATISTICS",
    "ARCHITECTURE_BENEFITS"
]