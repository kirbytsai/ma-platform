"""
MongoDB 資料庫連接管理
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError
from typing import Optional
import asyncio

from app.core.config import settings


class Database:
    """資料庫管理類別"""
    
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls):
        """建立資料庫連接"""
        try:
            print("🔌 正在連接 MongoDB...")
            print(f"   連接 URL: {settings.database_url[:50]}...")  # 只顯示前50個字符保護隱私
            
            # 建立客戶端連接
            cls.client = AsyncIOMotorClient(
                settings.database_url,
                maxPoolSize=100,
                minPoolSize=10,
                maxIdleTimeMS=45000,
                serverSelectionTimeoutMS=5000,
                socketTimeoutMS=20000,
                connectTimeoutMS=10000
            )
            
            # 取得資料庫實例
            # MongoDB Atlas URL 通常已經包含資料庫名稱
            if "mongodb+srv://" in settings.database_url and "/" in settings.database_url.split("@")[1]:
                # Atlas URL 格式，從 URL 中提取資料庫名稱
                db_name = settings.database_url.split("/")[-1].split("?")[0]
                cls.database = cls.client[db_name]
                print(f"   使用 Atlas 資料庫: {db_name}")
            else:
                # 本地 MongoDB 或其他格式
                db_name = (settings.MONGODB_TEST_DB_NAME 
                          if settings.is_testing 
                          else settings.MONGODB_DB_NAME)
                cls.database = cls.client[db_name]
                print(f"   使用本地資料庫: {db_name}")
            
            # 測試連接
            await cls.client.admin.command('ping')
            
            # 建立索引
            await cls.create_indexes()
            
            print(f"✅ MongoDB 連接成功 (資料庫: {db_name})")
            
        except ServerSelectionTimeoutError:
            print("❌ MongoDB 連接超時")
            raise
        except Exception as e:
            print(f"❌ MongoDB 連接失敗: {e}")
            raise
    
    @classmethod
    async def disconnect(cls):
        """關閉資料庫連接"""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.database = None
            print("🔌 MongoDB 連接已關閉")
    
    @classmethod
    async def health_check(cls) -> bool:
        """檢查資料庫健康狀態"""
        try:
            if cls.client is None:
                return False
            
            await cls.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """取得資料庫實例"""
        if cls.database is None:
            raise RuntimeError("資料庫尚未連接")
        return cls.database
    
    @classmethod
    async def create_indexes(cls):
        """建立資料庫索引"""
        if cls.database is None:
            return
        
        try:
            # 用戶集合索引
            await cls.database.users.create_index("email", unique=True)
            await cls.database.users.create_index("role")
            await cls.database.users.create_index("created_at")
            await cls.database.users.create_index("is_active")
            
            # 提案集合索引
            await cls.database.proposals.create_index("creator_id")
            await cls.database.proposals.create_index("status")
            await cls.database.proposals.create_index("industry")
            await cls.database.proposals.create_index("created_at")
            await cls.database.proposals.create_index([
                ("company_info.industry", 1),
                ("financial_info.asking_price", 1)
            ])
            
            # 提案案例集合索引
            await cls.database.proposal_cases.create_index("proposal_id")
            await cls.database.proposal_cases.create_index("seller_id")
            await cls.database.proposal_cases.create_index("buyer_id")
            await cls.database.proposal_cases.create_index("status")
            await cls.database.proposal_cases.create_index("created_at")
            await cls.database.proposal_cases.create_index([
                ("buyer_id", 1),
                ("status", 1),
                ("created_at", -1)
            ])
            
            # 訊息集合索引
            await cls.database.messages.create_index("case_id")
            await cls.database.messages.create_index("sender_id")
            await cls.database.messages.create_index("created_at")
            await cls.database.messages.create_index([
                ("case_id", 1),
                ("created_at", 1)
            ])
            
            # 通知集合索引
            await cls.database.notifications.create_index("user_id")
            await cls.database.notifications.create_index("is_read")
            await cls.database.notifications.create_index("notification_type")
            await cls.database.notifications.create_index("created_at")
            await cls.database.notifications.create_index([
                ("user_id", 1),
                ("is_read", 1),
                ("created_at", -1)
            ])
            
            # 審計日誌集合索引
            await cls.database.audit_logs.create_index("user_id")
            await cls.database.audit_logs.create_index("action")
            await cls.database.audit_logs.create_index("resource_type")
            await cls.database.audit_logs.create_index("created_at")
            
            # 檔案上傳集合索引
            await cls.database.file_uploads.create_index("uploader_id")
            await cls.database.file_uploads.create_index("proposal_id")
            await cls.database.file_uploads.create_index("case_id")
            await cls.database.file_uploads.create_index("created_at")
            
            print("✅ 資料庫索引建立完成")
            
        except Exception as e:
            print(f"⚠️ 索引建立過程中發生錯誤: {e}")
    
    @classmethod
    async def drop_database(cls):
        """刪除資料庫 (僅用於測試)"""
        if cls.database is not None and settings.is_testing:
            await cls.client.drop_database(cls.database.name)
            print(f"🗑️ 測試資料庫已刪除: {cls.database.name}")
    
    @classmethod
    async def clear_collections(cls, collections: list = None):
        """清空指定集合 (僅用於測試)"""
        if cls.database is None or not settings.is_testing:
            return
        
        if collections is None:
            collections = [
                "users", "proposals", "proposal_cases", 
                "messages", "notifications", "audit_logs", "file_uploads"
            ]
        
        for collection_name in collections:
            await cls.database[collection_name].delete_many({})
        
        print(f"🧹 已清空集合: {', '.join(collections)}")


# 依賴注入：取得資料庫實例
async def get_database() -> AsyncIOMotorDatabase:
    """依賴注入：取得資料庫實例"""
    return Database.get_database()