 
"""
安全相關工具函數
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings


# 密碼加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 認證
security = HTTPBearer()


def hash_password(password: str) -> str:
    """加密密碼"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """建立 JWT 存取 Token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """建立 JWT 刷新 Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_REFRESH_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """驗證 JWT Token"""
    try:
        secret = (settings.JWT_SECRET if token_type == "access" 
                 else settings.JWT_REFRESH_SECRET)
        
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # 檢查 Token 類型
        if payload.get("type") != token_type:
            raise JWTError("Token 類型不匹配")
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 驗證失敗: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """從 Token 中取得當前用戶 ID"""
    payload = verify_token(credentials.credentials)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中缺少用戶資訊",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """取得當前用戶完整資訊"""
    from app.services.auth_service import AuthService
    
    user_id = await get_current_user_id(credentials)
    
    # 從資料庫取得用戶資訊
    auth_service = AuthService()
    user = await auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶帳號已停用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# 角色權限檢查裝飾器
def require_role(required_role: str):
    """要求特定角色權限"""
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 角色權限"
            )
        return current_user
    
    return role_checker


def require_roles(required_roles: list):
    """要求多個角色之一的權限"""
    async def roles_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user.get("role") not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {', '.join(required_roles)}"
            )
        return current_user
    
    return roles_checker


# 預定義的角色檢查器
require_admin = require_role("admin")
require_seller = require_role("seller")
require_buyer = require_role("buyer")
require_seller_or_admin = require_roles(["seller", "admin"])
require_buyer_or_admin = require_roles(["buyer", "admin"])