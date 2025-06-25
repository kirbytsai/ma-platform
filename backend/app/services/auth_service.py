"""
認證業務邏輯服務
處理用戶註冊、登入、Token 管理等認證相關的業務邏輯
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from jose import JWTError, jwt
import secrets
from motor.motor_asyncio import AsyncIOMotorCollection

from app.models.user import User, UserRole
from app.services.user_service import user_service
from app.core.config import settings
from app.core.exceptions import (
    BusinessException, 
    ValidationException, 
    PermissionDeniedException
)
from app.schemas.auth import TokenData


class AuthService:
    """認證服務類"""
    
    def __init__(self):
        # Token 配置
        self.access_token_expire_minutes = 24 * 60  # 24 小時
        self.refresh_token_expire_days = 7  # 7 天
        self.algorithm = "HS256"
        
        # 內存中的 refresh token 黑名單 (實際應用中應使用 Redis)
        self._refresh_token_blacklist = set()
    
    async def register_user(
        self,
        email: str,
        password: str,
        role: UserRole,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        profile_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[User, Dict[str, Any]]:
        """
        用戶註冊
        
        Args:
            email: 用戶電子郵件
            password: 用戶密碼
            role: 用戶角色
            first_name: 名字
            last_name: 姓氏
            phone: 電話號碼
            profile_data: 角色專屬初始資料
            
        Returns:
            Tuple[User, Dict]: 用戶物件和 Token 資料
            
        Raises:
            BusinessException: 註冊失敗
            ValidationException: 資料驗證錯誤
        """
        
        # MVP 階段不允許註冊管理員
        if role == UserRole.ADMIN:
            raise PermissionDeniedException(
                message="無法註冊管理員帳號",
                error_code="ADMIN_REGISTRATION_FORBIDDEN"
            )
        
        try:
            # 建立用戶
            user = await user_service.create_user(
                email=email,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                profile_data=profile_data
            )
            
            # 生成 Token
            tokens = self._generate_tokens(user)
            
            return user, tokens
            
        except Exception as e:
            if isinstance(e, (BusinessException, ValidationException)):
                raise
            raise BusinessException(
                message=f"註冊失敗: {str(e)}",
                error_code="REGISTRATION_ERROR"
            )
    
    async def authenticate_user(
        self,
        email: str,
        password: str,
        remember_me: bool = False
    ) -> Tuple[User, Dict[str, Any]]:
        """
        用戶登入認證
        
        Args:
            email: 用戶電子郵件
            password: 用戶密碼
            remember_me: 是否記住我 (延長 Token 有效期)
            
        Returns:
            Tuple[User, Dict]: 用戶物件和 Token 資料
            
        Raises:
            BusinessException: 認證失敗
        """
        
        try:
            # 查找用戶
            user = await user_service.get_user_by_email(email)
            if not user:
                raise BusinessException(
                    message="電子郵件或密碼錯誤",
                    error_code="INVALID_CREDENTIALS"
                )
            
            # 檢查帳號是否啟用
            if not user.is_active:
                raise BusinessException(
                    message="帳號已被停用，請聯絡管理員",
                    error_code="ACCOUNT_DISABLED"
                )
            
            # 驗證密碼
            if not user.verify_password(password):
                raise BusinessException(
                    message="電子郵件或密碼錯誤",
                    error_code="INVALID_CREDENTIALS"
                )
            
            # 生成 Token (如果記住我，延長有效期)
            if remember_me:
                tokens = self._generate_tokens(user, extend_expiry=True)
            else:
                tokens = self._generate_tokens(user)
            
            return user, tokens
            
        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            raise BusinessException(
                message=f"登入失敗: {str(e)}",
                error_code="LOGIN_ERROR"
            )
    
    def _generate_tokens(
        self, 
        user: User,
        extend_expiry: bool = False
    ) -> Dict[str, Any]:
        """
        生成 Access Token 和 Refresh Token
        
        Args:
            user: 用戶物件
            extend_expiry: 是否延長有效期
            
        Returns:
            Dict: Token 資料
        """
        
        # Access Token 有效期
        if extend_expiry:
            access_expire = timedelta(minutes=self.access_token_expire_minutes * 2)  # 延長2倍
            refresh_expire = timedelta(days=self.refresh_token_expire_days * 2)     # 延長2倍
        else:
            access_expire = timedelta(minutes=self.access_token_expire_minutes)
            refresh_expire = timedelta(days=self.refresh_token_expire_days)
        
        # 計算過期時間
        access_expire_time = datetime.utcnow() + access_expire
        refresh_expire_time = datetime.utcnow() + refresh_expire
        
        # Access Token 載荷
        access_payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "token_type": "access",
            "exp": access_expire_time,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16)  # JWT ID
        }
        
        # Refresh Token 載荷
        refresh_payload = {
            "user_id": user.id,
            "token_type": "refresh",
            "exp": refresh_expire_time,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16)  # JWT ID
        }
        
        # 生成 Token
        access_token = jwt.encode(
            access_payload, 
            settings.JWT_SECRET, 
            algorithm=self.algorithm
        )
        
        refresh_token = jwt.encode(
            refresh_payload, 
            settings.JWT_REFRESH_SECRET, 
            algorithm=self.algorithm
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_expire.total_seconds()),
            "refresh_expires_in": int(refresh_expire.total_seconds())
        }
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        使用 Refresh Token 刷新 Access Token
        
        Args:
            refresh_token: Refresh Token
            
        Returns:
            Dict: 新的 Access Token 資料
            
        Raises:
            BusinessException: Token 無效或過期
        """
        
        try:
            # 檢查 Token 是否在黑名單中
            if refresh_token in self._refresh_token_blacklist:
                raise BusinessException(
                    message="Refresh Token 已失效",
                    error_code="INVALID_REFRESH_TOKEN"
                )
            
            # 解碼 Refresh Token
            payload = jwt.decode(
                refresh_token, 
                settings.JWT_REFRESH_SECRET, 
                algorithms=[self.algorithm]
            )
            
            # 驗證 Token 類型
            if payload.get("token_type") != "refresh":
                raise BusinessException(
                    message="無效的 Token 類型",
                    error_code="INVALID_TOKEN_TYPE"
                )
            
            # 取得用戶
            user_id = payload.get("user_id")
            user = await user_service.get_user_by_id(user_id)
            
            if not user:
                raise BusinessException(
                    message="用戶不存在",
                    error_code="USER_NOT_FOUND"
                )
            
            if not user.is_active:
                raise BusinessException(
                    message="帳號已被停用",
                    error_code="ACCOUNT_DISABLED"
                )
            
            # 生成新的 Access Token
            access_expire = timedelta(minutes=self.access_token_expire_minutes)
            access_expire_time = datetime.utcnow() + access_expire
            
            access_payload = {
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "token_type": "access",
                "exp": access_expire_time,
                "iat": datetime.utcnow(),
                "jti": secrets.token_urlsafe(16)
            }
            
            new_access_token = jwt.encode(
                access_payload, 
                settings.JWT_SECRET, 
                algorithm=self.algorithm
            )
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": int(access_expire.total_seconds())
            }
            
        except JWTError:
            raise BusinessException(
                message="無效的 Refresh Token",
                error_code="INVALID_REFRESH_TOKEN"
            )
        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            raise BusinessException(
                message=f"Token 刷新失敗: {str(e)}",
                error_code="TOKEN_REFRESH_ERROR"
            )
    
    def verify_access_token(self, token: str) -> TokenData:
        """
        驗證 Access Token
        
        Args:
            token: Access Token
            
        Returns:
            TokenData: Token 資料
            
        Raises:
            BusinessException: Token 無效或過期
        """
        
        try:
            # 解碼 Token
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=[self.algorithm]
            )
            
            # 驗證 Token 類型
            if payload.get("token_type") != "access":
                raise BusinessException(
                    message="無效的 Token 類型",
                    error_code="INVALID_TOKEN_TYPE"
                )
            
            # 提取 Token 資料
            user_id = payload.get("user_id")
            email = payload.get("email")
            role = payload.get("role")
            exp = payload.get("exp")
            
            if not all([user_id, email, role, exp]):
                raise BusinessException(
                    message="Token 資料不完整",
                    error_code="INCOMPLETE_TOKEN_DATA"
                )
            
            # 檢查過期時間
            exp_datetime = datetime.fromtimestamp(exp)
            if exp_datetime < datetime.utcnow():
                raise BusinessException(
                    message="Token 已過期",
                    error_code="TOKEN_EXPIRED"
                )
            
            return TokenData(
                user_id=user_id,
                email=email,
                role=UserRole(role),
                exp=exp_datetime,
                token_type="access"
            )
            
        except JWTError:
            raise BusinessException(
                message="無效的 Access Token",
                error_code="INVALID_ACCESS_TOKEN"
            )
    
    async def get_current_user(self, token: str) -> User:
        """
        根據 Token 取得當前用戶
        
        Args:
            token: Access Token
            
        Returns:
            User: 用戶物件
            
        Raises:
            BusinessException: Token 無效或用戶不存在
        """
        
        # 驗證 Token
        token_data = self.verify_access_token(token)
        
        # 取得用戶
        user = await user_service.get_user_by_id(token_data.user_id)
        if not user:
            raise BusinessException(
                message="用戶不存在",
                error_code="USER_NOT_FOUND"
            )
        
        if not user.is_active:
            raise BusinessException(
                message="帳號已被停用",
                error_code="ACCOUNT_DISABLED"
            )
        
        return user
    
    async def logout_user(self, refresh_token: str) -> bool:
        """
        用戶登出 (將 Refresh Token 加入黑名單)
        
        Args:
            refresh_token: Refresh Token
            
        Returns:
            bool: 登出是否成功
        """
        
        try:
            # 驗證 Refresh Token 格式
            jwt.decode(
                refresh_token, 
                settings.JWT_REFRESH_SECRET, 
                algorithms=[self.algorithm]
            )
            
            # 將 Token 加入黑名單
            self._refresh_token_blacklist.add(refresh_token)
            
            return True
            
        except JWTError:
            # 即使 Token 無效，也視為登出成功
            return True
        except Exception:
            return False
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        修改用戶密碼
        
        Args:
            user_id: 用戶 ID
            current_password: 目前密碼
            new_password: 新密碼
            
        Returns:
            bool: 修改是否成功
            
        Raises:
            BusinessException: 修改失敗
        """
        
        return await user_service.change_user_password(
            user_id=user_id,
            old_password=current_password,
            new_password=new_password
        )
    
    def check_user_permission(
        self, 
        user: User, 
        required_permission: str
    ) -> bool:
        """
        檢查用戶權限
        
        Args:
            user: 用戶物件
            required_permission: 需要的權限
            
        Returns:
            bool: 是否有權限
        """
        
        return user.has_permission(required_permission)
    
    def require_role(self, user: User, allowed_roles: list) -> bool:
        """
        檢查用戶角色
        
        Args:
            user: 用戶物件
            allowed_roles: 允許的角色列表
            
        Returns:
            bool: 角色是否符合
            
        Raises:
            PermissionDeniedException: 角色不符合
        """
        
        if user.role not in allowed_roles:
            raise PermissionDeniedException(
                message=f"此功能需要 {'/'.join(allowed_roles)} 角色權限",
                error_code="INSUFFICIENT_ROLE_PERMISSION"
            )
        
        return True
    
    def require_permission(self, user: User, permission: str) -> bool:
        """
        檢查特定權限
        
        Args:
            user: 用戶物件
            permission: 需要的權限
            
        Returns:
            bool: 是否有權限
            
        Raises:
            PermissionDeniedException: 權限不足
        """
        
        if not self.check_user_permission(user, permission):
            raise PermissionDeniedException(
                message=f"此功能需要 {permission} 權限",
                error_code="INSUFFICIENT_PERMISSION"
            )
        
        return True
    
    async def create_admin_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None
    ) -> User:
        """
        建立管理員用戶 (僅系統內部使用)
        
        Args:
            email: 管理員電子郵件
            password: 管理員密碼
            first_name: 名字
            last_name: 姓氏
            phone: 電話號碼
            
        Returns:
            User: 管理員用戶物件
            
        Raises:
            BusinessException: 建立失敗
        """
        
        return await user_service.create_user(
            email=email,
            password=password,
            role=UserRole.ADMIN,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
    
    def cleanup_expired_tokens(self):
        """
        清理過期的黑名單 Token (應定期執行)
        實際應用中應該使用 Redis 並設定 TTL
        """
        
        current_blacklist = self._refresh_token_blacklist.copy()
        
        for token in current_blacklist:
            try:
                # 嘗試解碼，如果過期會拋出異常
                jwt.decode(
                    token, 
                    settings.JWT_REFRESH_SECRET, 
                    algorithms=[self.algorithm]
                )
            except JWTError:
                # Token 無效或過期，從黑名單移除
                self._refresh_token_blacklist.discard(token)


# 全域認證服務實例
auth_service = AuthService()