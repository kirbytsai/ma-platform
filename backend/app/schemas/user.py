"""
用戶資料相關的 Pydantic 驗證模型
包含用戶資料展示、更新等功能的資料驗證
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime

from app.models.user import UserRole, InvestmentFocus, Industry, InvestmentRange


class UserResponse(BaseModel):
    """用戶資料回應模型 (不包含敏感資料)"""
    id: str = Field(..., description="用戶 ID")
    email: EmailStr = Field(..., description="用戶電子郵件")
    role: UserRole = Field(..., description="用戶角色")
    first_name: str = Field(..., description="名字")
    last_name: str = Field(..., description="姓氏")
    phone: Optional[str] = Field(None, description="電話號碼")
    is_active: bool = Field(..., description="帳號是否啟用")
    created_at: datetime = Field(..., description="建立時間")
    updated_at: datetime = Field(..., description="更新時間")
    
    # 角色專屬資料
    buyer_profile: Optional[Dict[str, Any]] = Field(None, description="買方專屬資料")
    seller_profile: Optional[Dict[str, Any]] = Field(None, description="提案方專屬資料")
    admin_profile: Optional[Dict[str, Any]] = Field(None, description="管理員專屬資料")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "60d5ecb54b24a1b2c8e4f1a2",
                "email": "buyer@example.com",
                "role": "buyer",
                "first_name": "小明",
                "last_name": "王",
                "phone": "+886-912-345-678",
                "is_active": True,
                "created_at": "2023-12-01T10:00:00Z",
                "updated_at": "2023-12-01T10:00:00Z",
                "buyer_profile": {
                    "company_name": "創投資本",
                    "investment_focus": ["technology"],
                    "investment_range": {"min": 1000000, "max": 10000000},
                    "preferred_industries": ["technology"],
                    "geographic_focus": "Asia"
                }
            }
        }
    }


class UserBasicUpdate(BaseModel):
    """用戶基本資料更新模型"""
    first_name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=50,
        description="名字"
    )
    last_name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=50,
        description="姓氏"
    )
    phone: Optional[str] = Field(
        None, 
        max_length=20,
        description="電話號碼"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "小華",
                "last_name": "李",
                "phone": "+886-987-654-321"
            }
        }
    }
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                raise ValueError("姓名不能為空")
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            v = v.strip()
            if v:
                cleaned = ''.join(filter(str.isdigit, v.replace('+', '').replace('-', '')))
                if len(cleaned) < 8:
                    raise ValueError("電話號碼格式不正確")
        return v


class BuyerProfileUpdate(BaseModel):
    """買方專屬資料更新模型"""
    company_name: Optional[str] = Field(
        None, 
        max_length=200,
        description="公司名稱"
    )
    investment_focus: Optional[List[InvestmentFocus]] = Field(
        None,
        description="投資重點"
    )
    investment_range: Optional[InvestmentRange] = Field(
        None,
        description="投資金額範圍"
    )
    preferred_industries: Optional[List[Industry]] = Field(
        None,
        description="偏好行業"
    )
    geographic_focus: Optional[str] = Field(
        None, 
        max_length=100,
        description="地理重點"
    )
    investment_criteria: Optional[str] = Field(
        None, 
        max_length=2000,
        description="投資標準和偏好"
    )
    portfolio_highlights: Optional[str] = Field(
        None, 
        max_length=2000,
        description="投資組合亮點"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "company_name": "亞洲創投基金",
                "investment_focus": ["technology", "healthcare"],
                "investment_range": {"min": 500000, "max": 5000000},
                "preferred_industries": ["technology", "healthcare"],
                "geographic_focus": "Southeast Asia",
                "investment_criteria": "尋找具有創新技術和強大團隊的早期公司",
                "portfolio_highlights": "已投資超過50家科技公司，總回報率300%"
            }
        }
    }
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                raise ValueError("公司名稱不能為空")
        return v
    
    @field_validator('investment_focus')
    @classmethod
    def validate_investment_focus(cls, v):
        if v is not None and len(v) > 5:
            raise ValueError("投資重點最多選擇5項")
        return v
    
    @field_validator('preferred_industries')
    @classmethod
    def validate_preferred_industries(cls, v):
        if v is not None and len(v) > 5:
            raise ValueError("偏好行業最多選擇5項")
        return v


class SellerProfileUpdate(BaseModel):
    """提案方專屬資料更新模型"""
    company_name: Optional[str] = Field(
        None, 
        max_length=200,
        description="公司名稱"
    )
    company_description: Optional[str] = Field(
        None, 
        max_length=2000,
        description="公司描述"
    )
    industry: Optional[Industry] = Field(
        None,
        description="所屬行業"
    )
    website: Optional[str] = Field(
        None, 
        max_length=255,
        description="公司網站"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "company_name": "創新科技有限公司",
                "company_description": "專注於人工智慧和機器學習解決方案的科技公司",
                "industry": "technology",
                "website": "https://example-tech.com"
            }
        }
    }
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                raise ValueError("公司名稱不能為空")
        return v
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        if v is not None:
            v = v.strip()
            if v and not (v.startswith('http://') or v.startswith('https://')):
                v = f"https://{v}"
        return v


class UserProfileUpdate(BaseModel):
    """統一的用戶資料更新模型"""
    # 基本資料更新
    basic_info: Optional[UserBasicUpdate] = Field(
        None,
        description="基本資料更新"
    )
    
    # 角色專屬資料更新
    buyer_profile: Optional[BuyerProfileUpdate] = Field(
        None,
        description="買方專屬資料更新"
    )
    seller_profile: Optional[SellerProfileUpdate] = Field(
        None,
        description="提案方專屬資料更新"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "basic_info": {
                    "first_name": "小華",
                    "phone": "+886-987-654-321"
                },
                "buyer_profile": {
                    "company_name": "新創投資",
                    "investment_focus": ["technology"]
                }
            }
        }
    }


class BuyerPublicProfile(BaseModel):
    """買方公開資料模型 (用於提案方查看)"""
    id: str = Field(..., description="買方 ID")
    company_name: Optional[str] = Field(None, description="公司名稱")
    investment_focus: List[InvestmentFocus] = Field(
        default_factory=list,
        description="投資重點"
    )
    investment_range: Optional[InvestmentRange] = Field(
        None,
        description="投資金額範圍"
    )
    preferred_industries: List[Industry] = Field(
        default_factory=list,
        description="偏好行業"
    )
    geographic_focus: Optional[str] = Field(None, description="地理重點")
    portfolio_highlights: Optional[str] = Field(None, description="投資組合亮點")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "60d5ecb54b24a1b2c8e4f1a2",
                "company_name": "亞洲創投基金",
                "investment_focus": ["technology", "healthcare"],
                "investment_range": {"min": 1000000, "max": 10000000},
                "preferred_industries": ["technology", "healthcare"],
                "geographic_focus": "Asia",
                "portfolio_highlights": "專注於早期科技投資，擁有豐富的產業經驗"
            }
        }
    }


class UserListResponse(BaseModel):
    """用戶列表回應模型"""
    users: List[UserResponse] = Field(..., description="用戶列表")
    total: int = Field(..., description="總用戶數")
    page: int = Field(..., description="當前頁碼")
    size: int = Field(..., description="每頁大小")
    has_next: bool = Field(..., description="是否有下一頁")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "users": [
                    {
                        "id": "60d5ecb54b24a1b2c8e4f1a2",
                        "email": "user1@example.com",
                        "role": "buyer",
                        "first_name": "小明",
                        "last_name": "王",
                        "is_active": True,
                        "created_at": "2023-12-01T10:00:00Z"
                    }
                ],
                "total": 150,
                "page": 1,
                "size": 20,
                "has_next": True
            }
        }
    }


class BuyerListResponse(BaseModel):
    """買方列表回應模型"""
    buyers: List[BuyerPublicProfile] = Field(..., description="買方公開資料列表")
    total: int = Field(..., description="總買方數")
    page: int = Field(..., description="當前頁碼")
    size: int = Field(..., description="每頁大小")
    has_next: bool = Field(..., description="是否有下一頁")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "buyers": [
                    {
                        "id": "60d5ecb54b24a1b2c8e4f1a2",
                        "company_name": "創投基金",
                        "investment_focus": ["technology"],
                        "investment_range": {"min": 1000000, "max": 10000000},
                        "preferred_industries": ["technology"],
                        "geographic_focus": "Asia"
                    }
                ],
                "total": 30,
                "page": 1,
                "size": 10,
                "has_next": True
            }
        }
    }


class UserStatistics(BaseModel):
    """用戶統計資料模型"""
    total_users: int = Field(..., description="總用戶數")
    active_users: int = Field(..., description="活躍用戶數")
    admin_total: int = Field(..., description="管理員總數")
    admin_active: int = Field(..., description="活躍管理員數")
    seller_total: int = Field(..., description="提案方總數")
    seller_active: int = Field(..., description="活躍提案方數")
    buyer_total: int = Field(..., description="買方總數")
    buyer_active: int = Field(..., description="活躍買方數")
    recent_registrations: int = Field(..., description="近期註冊數 (7天)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_users": 187,
                "active_users": 175,
                "admin_total": 2,
                "admin_active": 2,
                "seller_total": 25,
                "seller_active": 23,
                "buyer_total": 160,
                "buyer_active": 150,
                "recent_registrations": 12
            }
        }
    }