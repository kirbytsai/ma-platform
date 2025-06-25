"""
用戶資料模型
支援三種角色：admin, seller, buyer
包含角色專屬的嵌套資料結構
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from enum import Enum
import bcrypt
from bson import ObjectId


class UserRole(str, Enum):
    """用戶角色枚舉"""
    ADMIN = "admin"
    SELLER = "seller"
    BUYER = "buyer"


class InvestmentFocus(str, Enum):
    """投資重點枚舉"""
    TECHNOLOGY = "technology"
    MANUFACTURING = "manufacturing"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    RETAIL = "retail"
    REAL_ESTATE = "real_estate"
    ENERGY = "energy"
    EDUCATION = "education"
    FOOD_BEVERAGE = "food_beverage"
    OTHER = "other"


class Industry(str, Enum):
    """行業分類枚舉"""
    TECHNOLOGY = "technology"
    MANUFACTURING = "manufacturing"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    RETAIL = "retail"
    REAL_ESTATE = "real_estate"
    ENERGY = "energy"
    EDUCATION = "education"
    FOOD_BEVERAGE = "food_beverage"
    CONSULTING = "consulting"
    MEDIA = "media"
    LOGISTICS = "logistics"
    OTHER = "other"


class InvestmentRange(BaseModel):
    """投資金額範圍"""
    min: Optional[int] = Field(None, description="最小投資金額 (USD)")
    max: Optional[int] = Field(None, description="最大投資金額 (USD)")
    
    @field_validator('min', 'max')
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError("投資金額不能為負數")
        return v
    
    @model_validator(mode='after')
    def validate_range(self):
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise ValueError("最小投資金額不能大於最大投資金額")
        return self


class BuyerProfile(BaseModel):
    """買方專屬資料 (註冊時非必填，可後續編輯)"""
    company_name: Optional[str] = Field(None, max_length=200, description="公司名稱")
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
    geographic_focus: Optional[str] = Field(
        None, 
        max_length=100, 
        description="地理重點 (如: Asia, Global, North America)"
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
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("公司名稱不能為空")
        return v.strip() if v else v


class SellerProfile(BaseModel):
    """提案方專屬資料 (註冊時非必填，可後續編輯)"""
    company_name: Optional[str] = Field(None, max_length=200, description="公司名稱")
    company_description: Optional[str] = Field(
        None, 
        max_length=2000, 
        description="公司描述"
    )
    industry: Optional[Industry] = Field(None, description="所屬行業")
    website: Optional[str] = Field(None, max_length=255, description="公司網站")
    subscription_plan: str = Field(
        default="standard", 
        description="訂閱方案 (MVP階段固定為standard)"
    )
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("公司名稱不能為空")
        return v.strip() if v else v
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        if v is not None:
            v = v.strip()
            if v and not (v.startswith('http://') or v.startswith('https://')):
                v = f"https://{v}"
        return v


class AdminProfile(BaseModel):
    """管理員專屬資料 (系統預設)"""
    admin_level: str = Field(default="standard", description="管理員等級")
    permissions: List[str] = Field(default_factory=lambda: ["all"], description="權限列表")


class User(BaseModel):
    """
    用戶主模型
    支援三種角色：admin, seller, buyer
    """
    # MongoDB ObjectId (由系統自動生成)
    id: Optional[str] = Field(None, alias="_id", description="用戶唯一ID")
    
    # 基本資料 (所有角色必填)
    email: EmailStr = Field(..., description="用戶電子郵件 (唯一)")
    password_hash: str = Field(..., description="密碼雜湊值")
    role: UserRole = Field(..., description="用戶角色")
    first_name: str = Field(..., min_length=1, max_length=50, description="名字")
    last_name: str = Field(..., min_length=1, max_length=50, description="姓氏")
    phone: Optional[str] = Field(None, max_length=20, description="電話號碼")
    
    # 系統欄位
    is_active: bool = Field(default=True, description="帳號是否啟用")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="建立時間")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新時間")
    
    # 角色專屬資料 (根據角色類型使用)
    buyer_profile: Optional[BuyerProfile] = Field(None, description="買方專屬資料")
    seller_profile: Optional[SellerProfile] = Field(None, description="提案方專屬資料")
    admin_profile: Optional[AdminProfile] = Field(None, description="管理員專屬資料")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "email": "buyer@example.com",
                "password_hash": "$2b$12$...",
                "role": "buyer",
                "first_name": "張",
                "last_name": "小明",
                "phone": "+886-912-345-678",
                "is_active": True,
                "buyer_profile": {
                    "company_name": "創投資本",
                    "investment_focus": ["technology", "healthcare"],
                    "investment_range": {"min": 1000000, "max": 10000000},
                    "preferred_industries": ["technology", "healthcare"],
                    "geographic_focus": "Asia",
                    "investment_criteria": "尋找具有創新技術的成長期公司"
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
            # 移除空格和特殊字符進行基礎驗證
            cleaned = ''.join(filter(str.isdigit, v.replace('+', '').replace('-', '')))
            if len(cleaned) < 8:
                raise ValueError("電話號碼格式不正確")
        return v
    
    @model_validator(mode='after')
    def validate_role_profile_consistency(self):
        """驗證角色與專屬資料的一致性"""
        if self.role == UserRole.BUYER:
            if self.seller_profile is not None or self.admin_profile is not None:
                raise ValueError("買方角色不能有提案方或管理員資料")
        elif self.role == UserRole.SELLER:
            if self.buyer_profile is not None or self.admin_profile is not None:
                raise ValueError("提案方角色不能有買方或管理員資料")
        elif self.role == UserRole.ADMIN:
            if self.buyer_profile is not None or self.seller_profile is not None:
                raise ValueError("管理員角色不能有買方或提案方資料")
            # 確保管理員有 admin_profile
            if self.admin_profile is None:
                self.admin_profile = AdminProfile()
        
        return self
    
    # 密碼相關方法
    @staticmethod
    def hash_password(password: str) -> str:
        """密碼加密"""
        if len(password) < 8:
            raise ValueError("密碼長度至少需要8個字元")
        
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """密碼驗證"""
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            self.password_hash.encode('utf-8')
        )
    
    def set_password(self, password: str):
        """設定新密碼"""
        self.password_hash = self.hash_password(password)
        self.updated_at = datetime.utcnow()
    
    # 用戶資料管理方法
    def update_basic_info(self, **kwargs):
        """更新基本資料"""
        allowed_fields = {'first_name', 'last_name', 'phone'}
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(self, field):
                setattr(self, field, value)
        self.updated_at = datetime.utcnow()
    
    def update_profile(self, profile_data: dict):
        """更新角色專屬資料"""
        if self.role == UserRole.BUYER:
            if self.buyer_profile is None:
                self.buyer_profile = BuyerProfile()
            # 更新買方資料
            for key, value in profile_data.items():
                if hasattr(self.buyer_profile, key):
                    setattr(self.buyer_profile, key, value)
        
        elif self.role == UserRole.SELLER:
            if self.seller_profile is None:
                self.seller_profile = SellerProfile()
            # 更新提案方資料
            for key, value in profile_data.items():
                if hasattr(self.seller_profile, key):
                    setattr(self.seller_profile, key, value)
        
        self.updated_at = datetime.utcnow()
    
    # 權限檢查方法
    def has_permission(self, permission: str) -> bool:
        """檢查用戶權限"""
        if self.role == UserRole.ADMIN:
            # 管理員擁有所有權限
            return True
        
        # 角色專屬權限檢查
        role_permissions = {
            UserRole.SELLER: [
                "create_proposal", 
                "manage_own_proposal", 
                "view_cases",
                "send_proposal",
                "view_buyer_list"
            ],
            UserRole.BUYER: [
                "view_proposals", 
                "respond_to_proposals", 
                "manage_profile",
                "view_received_proposals",
                "sign_nda"
            ]
        }
        
        return permission in role_permissions.get(self.role, [])
    
    def can_create_proposal(self) -> bool:
        """檢查是否可以建立提案"""
        return self.role == UserRole.SELLER and self.is_active
    
    def can_respond_to_proposal(self) -> bool:
        """檢查是否可以回應提案"""
        return self.role == UserRole.BUYER and self.is_active
    
    def can_approve_proposal(self) -> bool:
        """檢查是否可以審核提案"""
        return self.role == UserRole.ADMIN and self.is_active
    
    # 軟刪除方法
    def soft_delete(self):
        """軟刪除用戶"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """啟用用戶"""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    # 資料完整度計算
    def get_profile_completeness(self) -> dict:
        """計算資料完整度"""
        completeness = {
            "score": 0,
            "total_fields": 0,
            "completed_fields": 0,
            "missing_fields": []
        }
        
        # 基本資料完整度 (40%)
        basic_fields = ['first_name', 'last_name', 'email']
        basic_completed = sum(1 for field in basic_fields if getattr(self, field))
        
        if self.role == UserRole.BUYER and self.buyer_profile:
            # 買方資料完整度
            profile_fields = [
                'company_name', 'investment_focus', 'investment_range',
                'preferred_industries', 'geographic_focus'
            ]
            profile_completed = 0
            for field in profile_fields:
                value = getattr(self.buyer_profile, field, None)
                if value:
                    if isinstance(value, list) and len(value) > 0:
                        profile_completed += 1
                    elif not isinstance(value, list):
                        profile_completed += 1
                else:
                    completeness["missing_fields"].append(f"buyer_profile.{field}")
            
            total_fields = len(basic_fields) + len(profile_fields)
            completed_fields = basic_completed + profile_completed
        
        elif self.role == UserRole.SELLER and self.seller_profile:
            # 提案方資料完整度
            profile_fields = ['company_name', 'company_description', 'industry']
            profile_completed = sum(
                1 for field in profile_fields 
                if getattr(self.seller_profile, field)
            )
            
            # 記錄缺少的欄位
            for field in profile_fields:
                if not getattr(self.seller_profile, field, None):
                    completeness["missing_fields"].append(f"seller_profile.{field}")
            
            total_fields = len(basic_fields) + len(profile_fields)
            completed_fields = basic_completed + profile_completed
        
        else:
            # 管理員或未設定專屬資料
            total_fields = len(basic_fields)
            completed_fields = basic_completed
        
        completeness["total_fields"] = total_fields
        completeness["completed_fields"] = completed_fields
        completeness["score"] = (completed_fields / total_fields * 100) if total_fields > 0 else 0
        
        return completeness
    
    # 修復 backend/app/models/user.py 中的 to_dict 方法

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """轉換為字典，可選擇是否包含敏感資料"""
        # 使用 Pydantic 的 model_dump 方法
        data = self.model_dump(by_alias=True, exclude_unset=False)
        
        # 處理 ObjectId 轉換
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        elif "id" in data and data["id"]:
            data["id"] = str(data["id"])
        
        # 移除敏感資料
        if not include_sensitive:
            data.pop('password_hash', None)
        
        # 確保必要欄位存在
        required_fields = {
            'email': self.email,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        # 補充缺失的必要欄位
        for field, value in required_fields.items():
            if field not in data:
                data[field] = value
        
        return data 
    
    def to_public_dict(self) -> dict:
        """輸出公開資料 (用於買方列表等場景)"""
        if self.role == UserRole.BUYER and self.buyer_profile:
            return {
                "id": self.id,
                "company_name": self.buyer_profile.company_name,
                "investment_focus": self.buyer_profile.investment_focus,
                "investment_range": self.buyer_profile.investment_range,
                "preferred_industries": self.buyer_profile.preferred_industries,
                "geographic_focus": self.buyer_profile.geographic_focus,
                "portfolio_highlights": self.buyer_profile.portfolio_highlights
            }
        return {
            "id": self.id,
            "role": self.role
        }


# 用戶工廠類別，用於建立不同角色的用戶
class UserFactory:
    """用戶工廠類別，簡化用戶建立流程"""
    
    @staticmethod
    def create_buyer(
        email: str, 
        password: str, 
        first_name: str, 
        last_name: str,
        phone: Optional[str] = None,
        buyer_profile_data: Optional[dict] = None
    ) -> User:
        """建立買方用戶"""
        buyer_profile = None
        if buyer_profile_data:
            buyer_profile = BuyerProfile(**buyer_profile_data)
        
        return User(
            email=email,
            password_hash=User.hash_password(password),
            role=UserRole.BUYER,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            buyer_profile=buyer_profile
        )
    
    @staticmethod
    def create_seller(
        email: str, 
        password: str, 
        first_name: str, 
        last_name: str,
        phone: Optional[str] = None,
        seller_profile_data: Optional[dict] = None
    ) -> User:
        """建立提案方用戶"""
        seller_profile = None
        if seller_profile_data:
            seller_profile = SellerProfile(**seller_profile_data)
        
        return User(
            email=email,
            password_hash=User.hash_password(password),
            role=UserRole.SELLER,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            seller_profile=seller_profile
        )
    
    @staticmethod
    def create_admin(
        email: str, 
        password: str, 
        first_name: str, 
        last_name: str,
        phone: Optional[str] = None
    ) -> User:
        """建立管理員用戶 (僅系統使用)"""
        return User(
            email=email,
            password_hash=User.hash_password(password),
            role=UserRole.ADMIN,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            admin_profile=AdminProfile()
        )