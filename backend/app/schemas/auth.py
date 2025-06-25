"""
認證相關的 Pydantic 驗證模型
包含註冊、登入、Token 管理等功能的資料驗證
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from datetime import datetime

from app.models.user import UserRole


class UserRegister(BaseModel):
    """用戶註冊請求模型"""
    email: EmailStr = Field(..., description="用戶電子郵件")
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=100,
        description="用戶密碼 (最少8字元)"
    )
    confirm_password: str = Field(
        ..., 
        min_length=8, 
        max_length=100,
        description="確認密碼"
    )
    role: UserRole = Field(..., description="用戶角色 (buyer/seller)")
    first_name: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="名字"
    )
    last_name: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="姓氏"
    )
    phone: Optional[str] = Field(
        None, 
        max_length=20,
        description="電話號碼 (可選)"
    )
    
    # 角色專屬初始資料 (可選)
    buyer_profile: Optional[Dict[str, Any]] = Field(
        None,
        description="買方初始資料 (可選)"
    )
    seller_profile: Optional[Dict[str, Any]] = Field(
        None,
        description="提案方初始資料 (可選)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "buyer@example.com",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
                "role": "buyer",
                "first_name": "小明",
                "last_name": "王",
                "phone": "+886-912-345-678",
                "buyer_profile": {
                    "company_name": "創投資本",
                    "investment_focus": ["technology"],
                    "geographic_focus": "Asia"
                }
            }
        }
    }
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("姓名不能為空")
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            v = v.strip()
            if v:
                # 基本電話號碼格式檢查
                cleaned = ''.join(filter(str.isdigit, v.replace('+', '').replace('-', '')))
                if len(cleaned) < 8:
                    raise ValueError("電話號碼格式不正確")
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        # MVP 階段不允許註冊管理員
        if v == UserRole.ADMIN:
            raise ValueError("無法註冊管理員帳號")
        return v
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("密碼與確認密碼不一致")
        return self
    
    @model_validator(mode='after')
    def validate_profile_consistency(self):
        """驗證角色與專屬資料的一致性"""
        if self.role == UserRole.BUYER:
            if self.seller_profile is not None:
                raise ValueError("買方角色不能提供提案方資料")
        elif self.role == UserRole.SELLER:
            if self.buyer_profile is not None:
                raise ValueError("提案方角色不能提供買方資料")
        return self


class UserLogin(BaseModel):
    """用戶登入請求模型"""
    email: EmailStr = Field(..., description="用戶電子郵件")
    password: str = Field(
        ..., 
        min_length=1,
        max_length=100,
        description="用戶密碼"
    )
    remember_me: bool = Field(
        default=False,
        description="記住我 (延長 Token 有效期)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "remember_me": False
            }
        }
    }


class TokenData(BaseModel):
    """Token 資料模型"""
    user_id: str = Field(..., description="用戶 ID")
    email: str = Field(..., description="用戶電子郵件")
    role: UserRole = Field(..., description="用戶角色")
    exp: datetime = Field(..., description="過期時間")
    token_type: str = Field(default="access", description="Token 類型")


class TokenResponse(BaseModel):
    """Token 回應模型"""
    access_token: str = Field(..., description="存取 Token")
    refresh_token: str = Field(..., description="刷新 Token")
    token_type: str = Field(default="bearer", description="Token 類型")
    expires_in: int = Field(..., description="存取 Token 有效期 (秒)")
    refresh_expires_in: int = Field(..., description="刷新 Token 有效期 (秒)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "refresh_expires_in": 604800
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    """刷新 Token 請求模型"""
    refresh_token: str = Field(..., description="刷新 Token")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }
    }


class AccessTokenResponse(BaseModel):
    """存取 Token 回應模型 (用於刷新)"""
    access_token: str = Field(..., description="新的存取 Token")
    token_type: str = Field(default="bearer", description="Token 類型")
    expires_in: int = Field(..., description="存取 Token 有效期 (秒)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }
    }


class PasswordChange(BaseModel):
    """修改密碼請求模型"""
    current_password: str = Field(
        ..., 
        min_length=1,
        max_length=100,
        description="目前密碼"
    )
    new_password: str = Field(
        ..., 
        min_length=8,
        max_length=100,
        description="新密碼 (最少8字元)"
    )
    confirm_new_password: str = Field(
        ..., 
        min_length=8,
        max_length=100,
        description="確認新密碼"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword456",
                "confirm_new_password": "newpassword456"
            }
        }
    }
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("新密碼與確認密碼不一致")
        return self
    
    @model_validator(mode='after')
    def validate_password_different(self):
        if self.current_password == self.new_password:
            raise ValueError("新密碼不能與目前密碼相同")
        return self


class UserRegisterResponse(BaseModel):
    """用戶註冊回應模型"""
    success: bool = Field(default=True, description="註冊是否成功")
    message: str = Field(default="註冊成功", description="回應訊息")
    user: Dict[str, Any] = Field(..., description="用戶資料")
    tokens: TokenResponse = Field(..., description="認證 Token")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "註冊成功",
                "user": {
                    "id": "60d5ecb54b24a1b2c8e4f1a2",
                    "email": "user@example.com",
                    "role": "buyer",
                    "first_name": "小明",
                    "last_name": "王",
                    "is_active": True,
                    "created_at": "2023-12-01T10:00:00Z"
                },
                "tokens": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer",
                    "expires_in": 86400,
                    "refresh_expires_in": 604800
                }
            }
        }
    }


class UserLoginResponse(BaseModel):
    """用戶登入回應模型"""
    success: bool = Field(default=True, description="登入是否成功")
    message: str = Field(default="登入成功", description="回應訊息")
    user: Dict[str, Any] = Field(..., description="用戶資料")
    tokens: TokenResponse = Field(..., description="認證 Token")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "登入成功",
                "user": {
                    "id": "60d5ecb54b24a1b2c8e4f1a2",
                    "email": "user@example.com",
                    "role": "buyer",
                    "first_name": "小明",
                    "last_name": "王",
                    "is_active": True
                },
                "tokens": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer",
                    "expires_in": 86400,
                    "refresh_expires_in": 604800
                }
            }
        }
    }


class LogoutResponse(BaseModel):
    """登出回應模型"""
    success: bool = Field(default=True, description="登出是否成功")
    message: str = Field(default="登出成功", description="回應訊息")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "登出成功"
            }
        }
    }


class PasswordChangeResponse(BaseModel):
    """修改密碼回應模型"""
    success: bool = Field(default=True, description="修改是否成功")
    message: str = Field(default="密碼修改成功", description="回應訊息")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "密碼修改成功"
            }
        }
    }


# 錯誤回應模型
class AuthErrorResponse(BaseModel):
    """認證錯誤回應模型"""
    success: bool = Field(default=False, description="操作是否成功")
    message: str = Field(..., description="錯誤訊息")
    error_code: Optional[str] = Field(None, description="錯誤代碼")
    details: Optional[Dict[str, Any]] = Field(None, description="錯誤詳情")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "message": "電子郵件已被註冊",
                "error_code": "USER_EMAIL_EXISTS",
                "details": {
                    "field": "email",
                    "value": "user@example.com"
                }
            }
        }
    }


# 用於 API 文檔的回應模型
class AuthResponses:
    """認證 API 的標準回應模型集合"""
    
    REGISTER_SUCCESS = {
        200: {
            "model": UserRegisterResponse,
            "description": "註冊成功"
        }
    }
    
    LOGIN_SUCCESS = {
        200: {
            "model": UserLoginResponse,
            "description": "登入成功"
        }
    }
    
    LOGOUT_SUCCESS = {
        200: {
            "model": LogoutResponse,
            "description": "登出成功"
        }
    }
    
    TOKEN_REFRESH_SUCCESS = {
        200: {
            "model": AccessTokenResponse,
            "description": "Token 刷新成功"
        }
    }
    
    PASSWORD_CHANGE_SUCCESS = {
        200: {
            "model": PasswordChangeResponse,
            "description": "密碼修改成功"
        }
    }
    
    AUTH_ERRORS = {
        400: {
            "model": AuthErrorResponse,
            "description": "請求資料錯誤"
        },
        401: {
            "model": AuthErrorResponse,
            "description": "認證失敗"
        },
        403: {
            "model": AuthErrorResponse,
            "description": "權限不足"
        },
        409: {
            "model": AuthErrorResponse,
            "description": "資料衝突 (如 email 重複)"
        },
        422: {
            "model": AuthErrorResponse,
            "description": "資料驗證錯誤"
        }
    }