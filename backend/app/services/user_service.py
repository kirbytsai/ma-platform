"""
用戶服務層
處理用戶相關的業務邏輯，包括 CRUD 操作、查詢、驗證等
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError
from pymongo import ASCENDING, DESCENDING

from app.models.user import User, UserRole, UserFactory
from app.core.database import get_database
from app.core.exceptions import (
    BusinessException, 
    ValidationException, 
    PermissionDeniedException
)


class UserService:
    """用戶服務類"""
    
    def __init__(self):
        self.db = None
        self.collection: Optional[AsyncIOMotorCollection] = None
    
    async def _get_collection(self) -> AsyncIOMotorCollection:
        """取得用戶集合"""
        if self.collection is None:
            self.db = await get_database()
            self.collection = self.db.users
        return self.collection
    
    # 建立用戶方法
    async def create_user(
        self, 
        email: str,
        password: str,
        role: UserRole,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        profile_data: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        建立新用戶
        
        Args:
            email: 用戶電子郵件
            password: 用戶密碼
            role: 用戶角色
            first_name: 名字
            last_name: 姓氏
            phone: 電話號碼 (可選)
            profile_data: 角色專屬資料 (可選)
        
        Returns:
            User: 建立的用戶物件
            
        Raises:
            ValidationException: 資料驗證錯誤
            BusinessException: 業務邏輯錯誤 (如 email 重複)
        """
        collection = await self._get_collection()
        
        # 檢查 email 是否已存在
        existing_user = await collection.find_one({"email": email})
        if existing_user:
            raise BusinessException(
                message="此電子郵件已被註冊",
                error_code="USER_EMAIL_EXISTS"
            )
        
        # 建立用戶物件
        try:
            if role == UserRole.BUYER:
                user = UserFactory.create_buyer(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    buyer_profile_data=profile_data
                )
            elif role == UserRole.SELLER:
                user = UserFactory.create_seller(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    seller_profile_data=profile_data
                )
            elif role == UserRole.ADMIN:
                # 管理員只能由系統建立
                user = UserFactory.create_admin(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone
                )
            else:
                raise ValidationException(
                    message="無效的用戶角色",
                    error_code="INVALID_USER_ROLE"
                )
                
        except ValueError as e:
            raise ValidationException(
                message=str(e),
                error_code="USER_VALIDATION_ERROR"
            )
        
        # 儲存到資料庫
        try:
            user_dict = user.model_dump(by_alias=True, exclude_unset=True)
            user_dict.pop('id', None)  # 移除 id，讓 MongoDB 自動生成
            
            result = await collection.insert_one(user_dict)
            user.id = str(result.inserted_id)
            
            return user
            
        except DuplicateKeyError:
            raise BusinessException(
                message="此電子郵件已被註冊",
                error_code="USER_EMAIL_EXISTS"
            )
        except Exception as e:
            raise BusinessException(
                message=f"用戶建立失敗: {str(e)}",
                error_code="USER_CREATE_ERROR"
            )
    
    # 查詢用戶方法
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根據 ID 查詢用戶"""
        collection = await self._get_collection()
        
        try:
            user_data = await collection.find_one({"_id": ObjectId(user_id)})
            if user_data:
                # 修復：確保正確轉換 ObjectId
                user_data["id"] = str(user_data["_id"])
                del user_data["_id"]  # 移除原始的 _id
                return User(**user_data)
            return None
            
        except Exception as e:
            raise BusinessException(
                message=f"查詢用戶失敗: {str(e)}",
                error_code="USER_QUERY_ERROR"
            )
        
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根據 email 查詢用戶"""
        collection = await self._get_collection()
        
        try:
            user_data = await collection.find_one({"email": email})
            if user_data:
                # 修復：確保正確轉換 ObjectId
                user_data["id"] = str(user_data["_id"])
                del user_data["_id"]  # 移除原始的 _id
                return User(**user_data)
            return None
            
        except Exception as e:
            raise BusinessException(
                message=f"查詢用戶失敗: {str(e)}",
                error_code="USER_QUERY_ERROR"
            )
        
    async def get_users_by_role(
        self, 
        role: UserRole,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[User]:
        """根據角色查詢用戶列表"""
        collection = await self._get_collection()
        
        try:
            filter_dict = {"role": role}
            if is_active is not None:
                filter_dict["is_active"] = is_active
            
            cursor = collection.find(filter_dict)
            cursor = cursor.sort("created_at", DESCENDING)
            cursor = cursor.skip(skip).limit(limit)
            
            users = []
            async for user_data in cursor:
                user_data["id"] = str(user_data["_id"])
                users.append(User(**user_data))
            
            return users
            
        except Exception as e:
            raise BusinessException(
                message=f"查詢用戶列表失敗: {str(e)}",
                error_code="USER_LIST_QUERY_ERROR"
            )
    
    async def count_users_by_role(
        self, 
        role: UserRole,
        is_active: Optional[bool] = None
    ) -> int:
        """計算指定角色的用戶數量"""
        collection = await self._get_collection()
        
        try:
            filter_dict = {"role": role}
            if is_active is not None:
                filter_dict["is_active"] = is_active
            
            return await collection.count_documents(filter_dict)
            
        except Exception as e:
            raise BusinessException(
                message=f"計算用戶數量失敗: {str(e)}",
                error_code="USER_COUNT_ERROR"
            )
    
    # 更新用戶方法
    async def update_user_basic_info(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[User]:
        """更新用戶基本資料"""
        collection = await self._get_collection()
        
        try:
            # 允許更新的基本欄位
            allowed_fields = {'first_name', 'last_name', 'phone'}
            filtered_data = {
                k: v for k, v in update_data.items() 
                if k in allowed_fields
            }
            
            if not filtered_data:
                raise ValidationException(
                    message="沒有可更新的欄位",
                    error_code="NO_UPDATE_FIELDS"
                )
            
            # 添加更新時間
            filtered_data['updated_at'] = datetime.utcnow()
            
            # 執行更新
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": filtered_data}
            )
            
            if result.modified_count == 0:
                return None
            
            # 返回更新後的用戶
            return await self.get_user_by_id(user_id)
            
        except Exception as e:
            raise BusinessException(
                message=f"更新用戶基本資料失敗: {str(e)}",
                error_code="USER_UPDATE_ERROR"
            )
    
    async def update_user_profile(
        self,
        user_id: str,
        profile_data: Dict[str, Any]
    ) -> Optional[User]:
        """更新用戶角色專屬資料"""
        collection = await self._get_collection()
        
        try:
            # 先取得用戶以確認角色
            user = await self.get_user_by_id(user_id)
            if not user:
                return None
            
            # 根據角色處理專屬資料
            update_dict = {"updated_at": datetime.utcnow()}
            
            if user.role == UserRole.BUYER:
                # 更新買方資料
                for key, value in profile_data.items():
                    if key in ['company_name', 'investment_focus', 'investment_range',
                             'preferred_industries', 'geographic_focus', 
                             'investment_criteria', 'portfolio_highlights']:
                        update_dict[f"buyer_profile.{key}"] = value
            
            elif user.role == UserRole.SELLER:
                # 更新提案方資料
                for key, value in profile_data.items():
                    if key in ['company_name', 'company_description', 
                             'industry', 'website']:
                        update_dict[f"seller_profile.{key}"] = value
            
            else:
                raise ValidationException(
                    message="此角色不支援資料更新",
                    error_code="ROLE_UPDATE_NOT_SUPPORTED"
                )
            
            if len(update_dict) == 1:  # 只有 updated_at
                raise ValidationException(
                    message="沒有可更新的專屬資料欄位",
                    error_code="NO_PROFILE_UPDATE_FIELDS"
                )
            
            # 執行更新
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count == 0:
                return None
            
            # 返回更新後的用戶
            return await self.get_user_by_id(user_id)
            
        except Exception as e:
            raise BusinessException(
                message=f"更新用戶專屬資料失敗: {str(e)}",
                error_code="USER_PROFILE_UPDATE_ERROR"
            )
    
    async def change_user_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """修改用戶密碼"""
        try:
            # 取得用戶
            user = await self.get_user_by_id(user_id)
            if not user:
                raise BusinessException(
                    message="用戶不存在",
                    error_code="USER_NOT_FOUND"
                )
            
            # 驗證舊密碼
            if not user.verify_password(old_password):
                raise BusinessException(
                    message="舊密碼不正確",
                    error_code="INVALID_OLD_PASSWORD"
                )
            
            # 更新密碼
            collection = await self._get_collection()
            new_password_hash = User.hash_password(new_password)
            
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "password_hash": new_password_hash,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise BusinessException(
                message=f"修改密碼失敗: {str(e)}",
                error_code="PASSWORD_CHANGE_ERROR"
            )
    
    # 用戶狀態管理
    async def activate_user(self, user_id: str) -> bool:
        """啟用用戶"""
        collection = await self._get_collection()
        
        try:
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "is_active": True,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise BusinessException(
                message=f"啟用用戶失敗: {str(e)}",
                error_code="USER_ACTIVATE_ERROR"
            )
    
    async def deactivate_user(self, user_id: str) -> bool:
        """停用用戶 (軟刪除)"""
        collection = await self._get_collection()
        
        try:
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise BusinessException(
                message=f"停用用戶失敗: {str(e)}",
                error_code="USER_DEACTIVATE_ERROR"
            )
    
    # 買方專用方法
    async def get_buyer_profiles(
        self,
        include_incomplete: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """取得買方公開資料列表 (用於提案方查看)"""
        collection = await self._get_collection()
        
        try:
            filter_dict = {
                "role": UserRole.BUYER,
                "is_active": True
            }
            
            # 如果不包含不完整資料，則篩選有公司名稱的買方
            if not include_incomplete:
                filter_dict["buyer_profile.company_name"] = {"$exists": True, "$ne": None}
            
            cursor = collection.find(filter_dict)
            cursor = cursor.sort("created_at", DESCENDING)
            cursor = cursor.skip(skip).limit(limit)
            
            buyer_profiles = []
            async for user_data in cursor:
                user_data["id"] = str(user_data["_id"])
                user = User(**user_data)
                
                # 取得公開資料
                public_data = user.to_public_dict()
                if public_data.get("company_name"):  # 確保有基本資料
                    buyer_profiles.append(public_data)
            
            return buyer_profiles
            
        except Exception as e:
            raise BusinessException(
                message=f"取得買方資料失敗: {str(e)}",
                error_code="BUYER_PROFILES_QUERY_ERROR"
            )
    
    async def search_buyers_by_criteria(
        self,
        investment_focus: Optional[List[str]] = None,
        preferred_industries: Optional[List[str]] = None,
        min_investment: Optional[int] = None,
        max_investment: Optional[int] = None,
        geographic_focus: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """根據條件搜尋買方"""
        collection = await self._get_collection()
        
        try:
            filter_dict = {
                "role": UserRole.BUYER,
                "is_active": True,
                "buyer_profile.company_name": {"$exists": True, "$ne": None}
            }
            
            # 投資重點篩選
            if investment_focus:
                filter_dict["buyer_profile.investment_focus"] = {"$in": investment_focus}
            
            # 偏好行業篩選
            if preferred_industries:
                filter_dict["buyer_profile.preferred_industries"] = {"$in": preferred_industries}
            
            # 投資金額範圍篩選
            if min_investment is not None:
                filter_dict["buyer_profile.investment_range.max"] = {"$gte": min_investment}
            
            if max_investment is not None:
                filter_dict["buyer_profile.investment_range.min"] = {"$lte": max_investment}
            
            # 地理重點篩選
            if geographic_focus:
                filter_dict["buyer_profile.geographic_focus"] = {
                    "$regex": geographic_focus, "$options": "i"
                }
            
            cursor = collection.find(filter_dict).limit(limit)
            
            results = []
            async for user_data in cursor:
                user_data["id"] = str(user_data["_id"])
                user = User(**user_data)
                results.append(user.to_public_dict())
            
            return results
            
        except Exception as e:
            raise BusinessException(
                message=f"搜尋買方失敗: {str(e)}",
                error_code="BUYER_SEARCH_ERROR"
            )
    
    # 統計方法
    async def get_user_statistics(self) -> Dict[str, Any]:
        """取得用戶統計資料"""
        collection = await self._get_collection()
        
        try:
            stats = {}
            
            # 各角色用戶數量
            for role in UserRole:
                stats[f"{role}_total"] = await collection.count_documents({"role": role})
                stats[f"{role}_active"] = await collection.count_documents({
                    "role": role, 
                    "is_active": True
                })
            
            # 總用戶數
            stats["total_users"] = await collection.count_documents({})
            stats["active_users"] = await collection.count_documents({"is_active": True})
            
            # 最近註冊統計 (7天內)
            seven_days_ago = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            seven_days_ago = seven_days_ago.replace(
                day=seven_days_ago.day - 7
            )
            
            stats["recent_registrations"] = await collection.count_documents({
                "created_at": {"$gte": seven_days_ago}
            })
            
            return stats
            
        except Exception as e:
            raise BusinessException(
                message=f"取得統計資料失敗: {str(e)}",
                error_code="USER_STATS_ERROR"
            )


# 全域用戶服務實例
user_service = UserService()