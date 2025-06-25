"""
MongoDB 資料庫索引建立腳本
為 M&A 平台建立必要的索引以優化查詢效能
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


class DatabaseIndexManager:
    """資料庫索引管理器"""
    
    def __init__(self):
        self.client = None
        self.database = None
    
    async def connect(self):
        """連接到 MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.database = self.client[settings.DATABASE_NAME]
            
            # 測試連接
            await self.client.admin.command('ping')
            print(f"✅ 成功連接到 MongoDB: {settings.DATABASE_NAME}")
            
        except Exception as e:
            print(f"❌ MongoDB 連接失敗: {e}")
            raise
    
    async def close(self):
        """關閉資料庫連接"""
        if self.client:
            self.client.close()
            print("🔒 資料庫連接已關閉")
    
    async def create_user_indexes(self):
        """建立用戶集合的索引"""
        collection = self.database.users
        
        print("🔧 建立用戶集合索引...")
        
        indexes_to_create = [
            # 1. Email 唯一索引 (最重要)
            {
                "name": "email_unique",
                "keys": [("email", ASCENDING)],
                "options": {"unique": True, "background": True}
            },
            
            # 2. 角色索引 (用於角色篩選)
            {
                "name": "role_index",
                "keys": [("role", ASCENDING)],
                "options": {"background": True}
            },
            
            # 3. 建立時間索引 (用於排序和時間範圍查詢)
            {
                "name": "created_at_index",
                "keys": [("created_at", DESCENDING)],
                "options": {"background": True}
            },
            
            # 4. 帳號狀態索引 (用於篩選啟用用戶)
            {
                "name": "is_active_index",
                "keys": [("is_active", ASCENDING)],
                "options": {"background": True}
            },
            
            # 5. 複合索引：角色 + 帳號狀態 (最常用的查詢組合)
            {
                "name": "role_active_compound",
                "keys": [("role", ASCENDING), ("is_active", ASCENDING)],
                "options": {"background": True}
            },
            
            # 6. 複合索引：角色 + 建立時間 (用於分頁查詢)
            {
                "name": "role_created_compound",
                "keys": [("role", ASCENDING), ("created_at", DESCENDING)],
                "options": {"background": True}
            },
            
            # 7. 買方投資重點索引 (用於媒合查詢)
            {
                "name": "buyer_investment_focus",
                "keys": [("buyer_profile.investment_focus", ASCENDING)],
                "options": {"background": True, "sparse": True}
            },
            
            # 8. 買方偏好行業索引 (用於媒合查詢)
            {
                "name": "buyer_preferred_industries",
                "keys": [("buyer_profile.preferred_industries", ASCENDING)],
                "options": {"background": True, "sparse": True}
            },
            
            # 9. 提案方行業索引 (用於分類查詢)
            {
                "name": "seller_industry",
                "keys": [("seller_profile.industry", ASCENDING)],
                "options": {"background": True, "sparse": True}
            },
            
            # 10. 文字搜尋索引 (公司名稱和描述)
            {
                "name": "text_search",
                "keys": [
                    ("buyer_profile.company_name", "text"),
                    ("seller_profile.company_name", "text"),
                    ("seller_profile.company_description", "text")
                ],
                "options": {"background": True, "sparse": True}
            }
        ]
        
        created_count = 0
        skipped_count = 0
        
        for index_spec in indexes_to_create:
            try:
                await collection.create_index(
                    index_spec["keys"], 
                    name=index_spec["name"],
                    **index_spec["options"]
                )
                print(f"  ✅ 索引 '{index_spec['name']}' 建立成功")
                created_count += 1
                
            except DuplicateKeyError:
                print(f"  ⚠️  索引 '{index_spec['name']}' 已存在，跳過")
                skipped_count += 1
                
            except OperationFailure as e:
                print(f"  ❌ 索引 '{index_spec['name']}' 建立失敗: {e}")
        
        print(f"📊 用戶索引建立完成: {created_count} 個新建立, {skipped_count} 個已存在")
    
    async def create_proposal_indexes(self):
        """建立提案集合的索引 (預留，後續實現)"""
        print("🔧 準備建立提案集合索引 (Phase 2 實現)...")
        
        # 預留提案相關索引
        # 這些索引將在 Phase 2 開發提案系統時實現
        proposal_indexes = [
            "creator_id_index",           # 建立者索引
            "status_index",              # 狀態索引
            "industry_index",            # 行業索引
            "asking_price_range_index",  # 要價範圍索引
            "created_at_index",          # 建立時間索引
        ]
        
        print(f"📋 預計建立 {len(proposal_indexes)} 個提案索引")
    
    async def create_case_indexes(self):
        """建立案例集合的索引 (預留，後續實現)"""
        print("🔧 準備建立案例集合索引 (Phase 3 實現)...")
        
        # 預留案例相關索引
        case_indexes = [
            "proposal_id_index",         # 提案 ID 索引
            "seller_id_index",          # 提案方 ID 索引
            "buyer_id_index",           # 買方 ID 索引
            "status_index",             # 狀態索引
            "created_at_index",         # 建立時間索引
        ]
        
        print(f"📋 預計建立 {len(case_indexes)} 個案例索引")
    
    async def list_existing_indexes(self):
        """列出現有索引"""
        print("\n📋 現有索引列表:")
        
        collections = ["users"]  # 目前只有用戶集合
        
        for collection_name in collections:
            collection = self.database[collection_name]
            try:
                indexes = await collection.list_indexes().to_list(length=None)
                print(f"\n📁 集合: {collection_name}")
                
                for index in indexes:
                    index_name = index.get('name', 'unnamed')
                    keys = index.get('key', {})
                    unique = index.get('unique', False)
                    sparse = index.get('sparse', False)
                    
                    key_desc = ', '.join([f"{k}: {v}" for k, v in keys.items()])
                    flags = []
                    if unique:
                        flags.append("unique")
                    if sparse:
                        flags.append("sparse")
                    
                    flag_str = f" ({', '.join(flags)})" if flags else ""
                    print(f"  📌 {index_name}: {key_desc}{flag_str}")
                    
            except Exception as e:
                print(f"  ❌ 無法列出 {collection_name} 索引: {e}")
    
    async def check_index_usage(self):
        """檢查索引使用情況 (簡化版本)"""
        print("\n📊 索引效能檢查:")
        
        collection = self.database.users
        
        # 檢查幾個常用查詢的執行計劃
        test_queries = [
            {"email": "test@example.com"},  # Email 查詢
            {"role": "buyer", "is_active": True},  # 角色 + 狀態查詢
            {"role": "seller"},  # 角色查詢
        ]
        
        for i, query in enumerate(test_queries, 1):
            try:
                explain = await collection.find(query).explain()
                winning_plan = explain.get('executionStats', {}).get('executionStages', {})
                stage = winning_plan.get('stage', 'unknown')
                
                if stage == 'IXSCAN':
                    print(f"  ✅ 查詢 {i}: 使用索引掃描")
                elif stage == 'COLLSCAN':
                    print(f"  ⚠️  查詢 {i}: 使用全集合掃描 (可能需要優化)")
                else:
                    print(f"  ℹ️  查詢 {i}: 執行階段 {stage}")
                    
            except Exception as e:
                print(f"  ❌ 查詢 {i} 檢查失敗: {e}")
    
    async def optimize_collection(self):
        """優化集合 (重建索引、壓縮等)"""
        print("\n🔧 優化用戶集合...")
        
        collection = self.database.users
        
        try:
            # 重建索引
            await collection.reindex()
            print("  ✅ 索引重建完成")
            
            # 取得集合統計資訊
            stats = await self.database.command("collStats", "users")
            doc_count = stats.get('count', 0)
            avg_obj_size = stats.get('avgObjSize', 0)
            storage_size = stats.get('storageSize', 0)
            
            print(f"  📊 文檔數量: {doc_count}")
            print(f"  📊 平均文檔大小: {avg_obj_size} bytes")
            print(f"  📊 存儲大小: {storage_size} bytes")
            
        except Exception as e:
            print(f"  ❌ 集合優化失敗: {e}")


async def main():
    """主執行函數"""
    print("🚀 開始建立 M&A 平台資料庫索引...")
    print("=" * 50)
    
    manager = DatabaseIndexManager()
    
    try:
        # 連接資料庫
        await manager.connect()
        
        # 列出現有索引
        await manager.list_existing_indexes()
        
        # 建立用戶索引
        await manager.create_user_indexes()
        
        # 預留其他集合索引建立
        await manager.create_proposal_indexes()
        await manager.create_case_indexes()
        
        # 檢查索引使用情況
        await manager.check_index_usage()
        
        # 優化集合
        await manager.optimize_collection()
        
        print("\n" + "=" * 50)
        print("🎉 資料庫索引建立完成！")
        
    except Exception as e:
        print(f"\n❌ 索引建立過程發生錯誤: {e}")
        raise
        
    finally:
        await manager.close()


if __name__ == "__main__":
    # 執行索引建立
    asyncio.run(main())