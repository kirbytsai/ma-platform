"""
API 依賴注入 (兼容版本)
整合現有業務邏輯依賴和新的認證系統
"""

from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import User, UserRole
from app.services.auth_service import auth_service
from app.core.database import get_database
from app.core.config import settings
from app.core.exceptions import BusinessException, PermissionDeniedException


# HTTP Bearer Token 認證
security = HTTPBearer(auto_error=False)


# ===== 基礎依賴 =====

async def get_db() -> AsyncIOMotorDatabase:
    """取得資料庫連接"""
    return await get_database()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    取得當前認證用戶 (整合版本)
    與原有的 core.security 兼容
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供認證 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user
        
    except BusinessException as e:
        if e.error_code in ["INVALID_ACCESS_TOKEN", "TOKEN_EXPIRED", "INCOMPLETE_TOKEN_DATA"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif e.error_code in ["USER_NOT_FOUND", "ACCOUNT_DISABLED"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="認證服務錯誤"
            )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """取得當前活躍用戶"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用"
        )
    return current_user


# ===== 角色依賴 (兼容原有風格) =====

async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """要求管理員權限"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此功能需要管理員權限"
        )
    return current_user


async def require_seller(current_user: User = Depends(get_current_active_user)) -> User:
    """要求提案方權限"""
    if current_user.role != UserRole.SELLER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此功能需要提案方權限"
        )
    return current_user


async def require_buyer(current_user: User = Depends(get_current_active_user)) -> User:
    """要求買方權限"""
    if current_user.role != UserRole.BUYER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此功能需要買方權限"
        )
    return current_user


# 兼容原有的角色依賴
async def get_current_admin(current_user: User = Depends(require_admin)) -> User:
    """取得當前管理員用戶 (兼容)"""
    return current_user


async def get_current_seller(current_user: User = Depends(require_seller)) -> User:
    """取得當前提案方用戶 (兼容)"""
    return current_user


async def get_current_buyer(current_user: User = Depends(require_buyer)) -> User:
    """取得當前買方用戶 (兼容)"""
    return current_user


# ===== 分頁和搜尋依賴 =====

def get_pagination_params(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(
        getattr(settings, 'DEFAULT_PAGE_SIZE', 20), 
        ge=1, 
        le=getattr(settings, 'MAX_PAGE_SIZE', 100), 
        description="每頁數量"
    )
) -> Dict[str, int]:
    """取得分頁參數 (兼容)"""
    skip = (page - 1) * page_size
    return {
        "skip": skip,
        "limit": page_size,
        "page": page,
        "page_size": page_size
    }


def get_search_params(
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    sort_by: Optional[str] = Query("created_at", description="排序欄位"),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$", description="排序順序")
) -> Dict[str, Any]:
    """取得搜尋和排序參數"""
    return {
        "search": search,
        "sort_by": sort_by,
        "sort_order": sort_order
    }


# ===== 業務邏輯驗證依賴 (保留原有邏輯) =====

async def verify_proposal_owner(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    """驗證提案擁有者"""
    from bson import ObjectId
    
    try:
        proposal = await db.proposals.find_one({"_id": ObjectId(proposal_id)})
    except:
        # 如果 ObjectId 格式錯誤
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的提案 ID 格式"
        )
    
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提案不存在"
        )
    
    # 管理員可以存取所有提案
    if current_user.role == UserRole.ADMIN:
        proposal["_id"] = str(proposal["_id"])  # 轉換 ObjectId 為字串
        return proposal
    
    # 提案方只能存取自己的提案
    if (current_user.role == UserRole.SELLER and 
        str(proposal.get("creator_id")) == current_user.id):
        proposal["_id"] = str(proposal["_id"])
        return proposal
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="您沒有權限存取此提案"
    )


async def verify_case_access(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    """驗證案例存取權限"""
    from bson import ObjectId
    
    try:
        case = await db.proposal_cases.find_one({"_id": ObjectId(case_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的案例 ID 格式"
        )
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="案例不存在"
        )
    
    user_id = current_user.id
    user_role = current_user.role
    
    # 管理員可以存取所有案例
    if user_role == UserRole.ADMIN:
        case["_id"] = str(case["_id"])
        return case
    
    # 案例相關的買方和提案方可以存取
    if user_id in [str(case.get("seller_id")), str(case.get("buyer_id"))]:
        case["_id"] = str(case["_id"])
        return case
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="您沒有權限存取此案例"
    )


# ===== 篩選依賴 (保留原有邏輯) =====

def get_proposal_filters(
    status: Optional[str] = Query(None, description="提案狀態"),
    industry: Optional[str] = Query(None, description="行業分類"),
    min_price: Optional[float] = Query(None, ge=0, description="最低價格"),
    max_price: Optional[float] = Query(None, ge=0, description="最高價格")
) -> Dict[str, Any]:
    """取得提案篩選參數"""
    filters = {}
    
    if status:
        filters["status"] = status
    
    if industry:
        filters["company_info.industry"] = industry
    
    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        filters["financial_info.asking_price"] = price_filter
    
    return filters


def get_case_filters(
    status: Optional[str] = Query(None, description="案例狀態"),
    proposal_id: Optional[str] = Query(None, description="提案 ID")
) -> Dict[str, Any]:
    """取得案例篩選參數"""
    filters = {}
    
    if status:
        filters["status"] = status
    
    if proposal_id:
        from bson import ObjectId
        try:
            filters["proposal_id"] = ObjectId(proposal_id)
        except:
            # 如果格式錯誤，返回空結果
            filters["proposal_id"] = "invalid"
    
    return filters


def get_notification_filters(
    is_read: Optional[bool] = Query(None, description="已讀狀態"),
    notification_type: Optional[str] = Query(None, description="通知類型")
) -> Dict[str, Any]:
    """取得通知篩選參數"""
    filters = {}
    
    if is_read is not None:
        filters["is_read"] = is_read
    
    if notification_type:
        filters["notification_type"] = notification_type
    
    return filters


# ===== 新增的通用依賴 =====

class PaginationParams:
    """分頁參數類 (新版本)"""
    
    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="頁碼"),
        size: int = Query(default=20, ge=1, le=100, description="每頁大小")
    ):
        self.page = page
        self.size = size
        self.skip = (page - 1) * size
        self.limit = size


def get_pagination_params_v2(
    page: int = Query(default=1, ge=1, description="頁碼"),
    size: int = Query(default=20, ge=1, le=100, description="每頁大小")
) -> PaginationParams:
    """取得分頁參數 (新版本)"""
    return PaginationParams(page=page, size=size)


# 可選的認證依賴
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """取得當前用戶 (可選)"""
    if not credentials:
        return None
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user if user.is_active else None
    except BusinessException:
        return None


# ===== 權限檢查工廠函數 =====

def require_roles(allowed_roles: List[UserRole]):
    """角色權限檢查依賴工廠"""
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            role_names = [role.value for role in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"此功能需要 {'/'.join(role_names)} 角色權限"
            )
        return current_user
    
    return role_checker


def require_permission(required_permission: str):
    """特定權限檢查依賴工廠"""
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        try:
            auth_service.require_permission(current_user, required_permission)
            return current_user
            
        except PermissionDeniedException as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message
            )
    
    return permission_checker


# 常用角色組合依賴
require_seller_or_admin = require_roles([UserRole.SELLER, UserRole.ADMIN])
require_buyer_or_admin = require_roles([UserRole.BUYER, UserRole.ADMIN])