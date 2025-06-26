"""
M&A 平台 MongoDB 資料庫索引建立腳本
為所有集合建立必要的索引以優化查詢效能
支援 Phase 1 (用戶) 和 Phase 2 (提案) 系統
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, TEXT
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
            print("🔌 正在連接 MongoDB...")
            self.client = AsyncIOMotorClient(settings.database_url)
            
            # 從 URL 解析資料庫名稱
            if "mongodb+srv://" in settings.database_url and "/" in settings.database_url.split("@")[1]:
                db_name = settings.database_url.split("/")[-1].split("?")[0]
            else:
                db_name = "ma_platform"
            
            self.database = self.client[db_name]
            
            # 測試連接
            await self.client.admin.command('ping')
            print(f"✅ 成功連接到 MongoDB: {db_name}")
            
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
                "keys": [("buyer_profile.public_profile.preferred_industries", ASCENDING)],
                "options": {"background": True, "sparse": True}
            },
            
            # 8. 文字搜尋索引 (公司名稱)
            {
                "name": "company_name_text",
                "keys": [
                    ("buyer_profile.public_profile.company_name", TEXT),
                    ("seller_profile.business_info.company_name", TEXT)
                ],
                "options": {"background": True, "sparse": True}
            }
        ]
        
        return await self._create_indexes_for_collection(collection, indexes_to_create, "用戶")
    
    async def create_proposal_indexes(self):
        """建立提案集合的索引"""
        collection = self.database.proposals
        
        print("🔧 建立提案集合索引...")
        
        indexes_to_create = [
            # 1. 建立者索引 (最重要 - 用於查詢用戶的提案)
            {
                "name": "creator_id_index",
                "keys": [("creator_id", ASCENDING)],
                "options": {"background": True}
            },
            
            # 2. 狀態索引 (用於狀態篩選)
            {
                "name": "status_index",
                "keys": [("status", ASCENDING)],
                "options": {"background": True}
            },
            
            # 3. 行業索引 (用於行業篩選)
            {
                "name": "industry_index",
                "keys": [("company_info.industry", ASCENDING)],
                "options": {"background": True}
            },
            
            # 4. 建立時間索引 (用於排序)
            {
                "name": "created_at_index",
                "keys": [("created_at", DESCENDING)],
                "options": {"background": True}
            },
            
            # 5. 是否啟用索引
            {
                "name": "is_active_index",
                "keys": [("is_active", ASCENDING)],
                "options": {"background": True}
            },
            
            # 6. 複合索引：狀態 + 建立時間 (管理員審核查詢)
            {
                "name": "status_created_compound",
                "keys": [("status", ASCENDING), ("created_at", DESCENDING)],
                "options": {"background": True}
            },
            
            # 7. 複合索引：建立者 + 狀態 (用戶查看自己的提案)
            {
                "name": "creator_status_compound",
                "keys": [("creator_id", ASCENDING), ("status", ASCENDING)],
                "options": {"background": True}
            },
            
            # 8. 複合索引：行業 + 狀態 (媒合查詢)
            {
                "name": "industry_status_compound",
                "keys": [("company_info.industry", ASCENDING), ("status", ASCENDING)],
                "options": {"background": True}
            },
            
            # 9. 複合索引：營收範圍 (媒合查詢)
            {
                "name": "revenue_range_index",
                "keys": [("financial_info.annual_revenue", ASCENDING)],
                "options": {"background": True}
            },
            
            # 10. 複合索引：要價範圍 (媒合查詢)
            {
                "name": "asking_price_index",
                "keys": [("financial_info.asking_price", ASCENDING)],
                "options": {"background": True}
            },
            
            # 11. 複合索引：公司規模 (媒合查詢)
            {
                "name": "company_size_index",
                "keys": [("company_info.company_size", ASCENDING)],
                "options": {"background": True}
            },
            
            # 12. 複合索引：地區 (媒合查詢)
            {
                "name": "headquarters_index",
                "keys": [("company_info.headquarters", ASCENDING)],
                "options": {"background": True}
            },
            
            # 13. 文字搜尋索引 (公司名稱和標題)
            {
                "name": "proposal_text_search",
                "keys": [
                    ("company_info.company_name", TEXT),
                    ("teaser_content.title", TEXT),
                    ("teaser_content.summary", TEXT)
                ],
                "options": {"background": True}
            },
            
            # 14. 複合索引：媒合查詢優化 (行業 + 營收 + 狀態)
            {
                "name": "matching_compound",
                "keys": [
                    ("company_info.industry", ASCENDING),
                    ("financial_info.annual_revenue", ASCENDING),
                    ("status", ASCENDING)
                ],
                "options": {"background": True}
            }
        ]
        
        return await self._create_indexes_for_collection(collection, indexes_to_create, "提案")
    
    async def create_case_indexes(self):
        """建立案例集合的索引 (預留 Phase 3)"""
        collection = self.database.proposal_cases
        
        print("🔧 建立案例集合索引 (預留 Phase 3)...")
        
        indexes_to_create = [
            # 1. 提案 ID 索引
            {
                "name": "proposal_id_index",
                "keys": [("proposal_id", ASCENDING)],
                "options": {"background": True}
            },
            
            # 2. 提案方 ID 索引
            {
                "name": "seller_id_index",
                "keys": [("seller_id", ASCENDING)],
                "options": {"background": True}
            },
            
            # 3. 買方 ID 索引
            {
                "name": "buyer_id_index",
                "keys": [("buyer_id", ASCENDING)],
                "options": {"background": True}
            },
            
            # 4. 狀態索引
            {
                "name": "status_index",
                "keys": [("status", ASCENDING)],
                "options": {"background": True}
            },
            
            # 5. 建立時間索引
            {
                "name": "created_at_index",
                "keys": [("created_at", DESCENDING)],
                "options": {"background": True}
            },
            
            # 6. 複合索引：買方 + 狀態 (買方收件箱)
            {
                "name": "buyer_status_compound",
                "keys": [("buyer_id", ASCENDING), ("status", ASCENDING)],
                "options": {"background": True}
            },
            
            # 7. 複合索引：提案方 + 狀態 (提案方發送記錄)
            {
                "name": "seller_status_compound",
                "keys": [("seller_id", ASCENDING), ("status", ASCENDING)],
                "options": {"background": True}
            }
        ]
        
        return await self._create_indexes_for_collection(collection, indexes_to_create, "案例")
    
    async def create_message_indexes(self):
        """建立訊息集合的索引 (預留 Phase 3)"""
        collection = self.database.messages
        
        print("🔧 建立訊息集合索引 (預留 Phase 3)...")
        
        indexes_to_create = [
            # 1. 案例 ID 索引
            {
                "name": "case_id_index",
                "keys": [("case_id", ASCENDING)],
                "options": {"background": True}
            },
            
            # 2. 發送者索引
            {
                "name": "sender_id_index",
                "keys": [("sender_id", ASCENDING)],
                "options": {"background": True}
            },
            
            # 3. 建立時間索引
            {
                "name": "created_at_index",
                "keys": [("created_at", DESCENDING)],
                "options": {"background": True}
            },
            
            # 4. 複合索引：案例 + 時間 (對話記錄查詢)
            {
                "name": "case_created_compound",
                "keys": [("case_id", ASCENDING), ("created_at", ASCENDING)],
                "options": {"background": True}
            }
        ]
        
        return await self._create_indexes_for_collection(collection, indexes_to_create, "訊息")
    
    async def create_notification_indexes(self):
        """建立通知集合的索引 (預留 Phase 4)"""
        collection = self.database.notifications
        
        print("🔧 建立通知集合索引 (預留 Phase 4)...")
        
        indexes_to_create = [
            # 1. 用戶 ID 索引
            {
                "name": "user_id_index",
                "keys": [("user_id", ASCENDING)],
                "options": {"background": True}
            },
            
            # 2. 已讀狀態索引
            {
                "name": "is_read_index",
                "keys": [("is_read", ASCENDING)],
                "options": {"background": True}
            },
            
            # 3. 建立時間索引
            {
                "name": "created_at_index",
                "keys": [("created_at", DESCENDING)],
                "options": {"background": True}
            },
            
            # 4. 複合索引：用戶 + 已讀狀態
            {
                "name": "user_read_compound",
                "keys": [("user_id", ASCENDING), ("is_read", ASCENDING)],
                "options": {"background": True}
            }
        ]
        
        return await self._create_indexes_for_collection(collection, indexes_to_create, "通知")
    
    async def _create_indexes_for_collection(self, collection, indexes_to_create, collection_name):
        """為指定集合建立索引"""
        created_count = 0
        skipped_count = 0
        failed_count = 0
        
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
                failed_count += 1
                
            except Exception as e:
                print(f"  ❌ 索引 '{index_spec['name']}' 建立錯誤: {e}")
                failed_count += 1
        
        print(f"📊 {collection_name}索引建立完成: {created_count} 個新建立, {skipped_count} 個已存在, {failed_count} 個失敗")
        return {"created": created_count, "skipped": skipped_count, "failed": failed_count}
    
    async def list_existing_indexes(self):
        """列出現有索引"""
        print("\n📋 現有索引列表:")
        
        collections = ["users", "proposals", "proposal_cases", "messages", "notifications"]
        
        for collection_name in collections:
            collection = self.database[collection_name]
            try:
                indexes = await collection.list_indexes().to_list(length=None)
                if indexes:
                    print(f"\n📁 集合: {collection_name}")
                    
                    for index in indexes:
                        index_name = index.get('name', 'unnamed')
                        keys = index.get('key', {})
                        unique = index.get('unique', False)
                        sparse = index.get('sparse', False)
                        text = index.get('textIndexVersion', None) is not None
                        
                        key_desc = ', '.join([f"{k}: {v}" for k, v in keys.items()])
                        flags = []
                        if unique:
                            flags.append("unique")
                        if sparse:
                            flags.append("sparse")
                        if text:
                            flags.append("text")
                        
                        flag_str = f" ({', '.join(flags)})" if flags else ""
                        print(f"  📌 {index_name}: {key_desc}{flag_str}")
                else:
                    print(f"\n📁 集合: {collection_name} (無索引)")
                    
            except Exception as e:
                print(f"  ❌ 無法列出 {collection_name} 索引: {e}")
    
    async def check_index_usage(self):
        """檢查索引使用情況"""
        print("\n📊 索引效能檢查:")
        
        # 檢查用戶集合
        await self._check_collection_queries("users", [
            {"email": "buyer1@example.com"},  # Email 查詢
            {"role": "buyer", "is_active": True},  # 角色 + 狀態查詢
            {"role": "seller"},  # 角色查詢
        ])
        
        # 檢查提案集合 (如果存在資料)
        proposals_count = await self.database.proposals.count_documents({})
        if proposals_count > 0:
            await self._check_collection_queries("proposals", [
                {"status": "approved"},  # 狀態查詢
                {"company_info.industry": "科技軟體"},  # 行業查詢
                {"creator_id": "64a1b2c3d4e5f6789012345"},  # 建立者查詢
            ])
        else:
            print("  ℹ️  提案集合無資料，跳過查詢檢查")
    
    async def _check_collection_queries(self, collection_name, test_queries):
        """檢查指定集合的查詢效能"""
        collection = self.database[collection_name]
        
        print(f"\n  📊 {collection_name} 集合查詢檢查:")
        
        for i, query in enumerate(test_queries, 1):
            try:
                explain = await collection.find(query).explain()
                winning_plan = explain.get('executionStats', {}).get('executionStages', {})
                stage = winning_plan.get('stage', 'unknown')
                
                if stage == 'IXSCAN':
                    print(f"    ✅ 查詢 {i}: 使用索引掃描")
                elif stage == 'COLLSCAN':
                    print(f"    ⚠️  查詢 {i}: 使用全集合掃描 (可能需要優化)")
                else:
                    print(f"    ℹ️  查詢 {i}: 執行階段 {stage}")
                    
            except Exception as e:
                print(f"    ❌ 查詢 {i} 檢查失敗: {e}")
    
    async def get_database_stats(self):
        """取得資料庫統計資訊"""
        print("\n📊 資料庫統計資訊:")
        
        try:
            db_stats = await self.database.command("dbStats")
            
            print(f"  📁 資料庫名稱: {db_stats.get('db', 'unknown')}")
            print(f"  📊 集合數量: {db_stats.get('collections', 0)}")
            print(f"  📊 索引數量: {db_stats.get('indexes', 0)}")
            print(f"  💾 資料大小: {db_stats.get('dataSize', 0):,} bytes")
            print(f"  💾 索引大小: {db_stats.get('indexSize', 0):,} bytes")
            print(f"  💾 總大小: {db_stats.get('storageSize', 0):,} bytes")
            
            # 各集合統計
            collections = ["users", "proposals", "proposal_cases", "messages", "notifications"]
            print(f"\n  📋 各集合文檔數量:")
            
            for collection_name in collections:
                try:
                    count = await self.database[collection_name].count_documents({})
                    print(f"    📄 {collection_name}: {count:,} 個文檔")
                except Exception as e:
                    print(f"    ❌ {collection_name}: 無法取得統計 ({e})")
                    
        except Exception as e:
            print(f"  ❌ 無法取得資料庫統計: {e}")


async def main():
    """主執行函數"""
    print("🚀 M&A 平台資料庫索引建立器")
    print("💫 支援 Phase 1 (用戶) + Phase 2 (提案) 系統")
    print("=" * 60)
    
    manager = DatabaseIndexManager()
    
    try:
        # 連接資料庫
        await manager.connect()
        
        # 列出現有索引
        await manager.list_existing_indexes()
        
        # 建立各集合索引
        print("\n🔧 開始建立索引...")
        print("=" * 40)
        
        user_stats = await manager.create_user_indexes()
        proposal_stats = await manager.create_proposal_indexes()
        case_stats = await manager.create_case_indexes()
        message_stats = await manager.create_message_indexes()
        notification_stats = await manager.create_notification_indexes()
        
        # 統計總結
        total_created = (user_stats["created"] + proposal_stats["created"] + 
                        case_stats["created"] + message_stats["created"] + 
                        notification_stats["created"])
        total_skipped = (user_stats["skipped"] + proposal_stats["skipped"] + 
                        case_stats["skipped"] + message_stats["skipped"] + 
                        notification_stats["skipped"])
        total_failed = (user_stats["failed"] + proposal_stats["failed"] + 
                       case_stats["failed"] + message_stats["failed"] + 
                       notification_stats["failed"])
        
        print(f"\n📊 索引建立總結:")
        print(f"  ✅ 新建立: {total_created} 個")
        print(f"  ⚠️  已存在: {total_skipped} 個")
        print(f"  ❌ 失敗: {total_failed} 個")
        
        # 檢查索引使用情況
        await manager.check_index_usage()
        
        # 取得資料庫統計
        await manager.get_database_stats()
        
        print("\n" + "=" * 60)
        print("🎉 資料庫索引建立完成！")
        print("🚀 M&A 平台已準備就緒！")
        
    except Exception as e:
        print(f"\n❌ 索引建立過程發生錯誤: {e}")
        raise
        
    finally:
        await manager.close()


if __name__ == "__main__":
    # 執行索引建立
    asyncio.run(main())