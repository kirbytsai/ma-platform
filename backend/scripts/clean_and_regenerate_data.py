#!/usr/bin/env python3
"""
M&A 平台測試資料清理和重新生成腳本
完全清除舊資料並生成最新版本的測試資料
專為 Phase 2 提案管理系統測試設計
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
from faker import Faker

# 添加 app 模組到路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import Database
from app.core.security import hash_password


class DataCleanerAndGenerator:
    """測試資料清理和重新生成器"""
    
    def __init__(self):
        self.fake = Faker(['zh_TW', 'en_US'])
        self.db = None
        
        # 行業分類（更新版）
        self.industries = [
            "科技軟體", "電子製造", "生物科技", "AI人工智慧", "金融科技",
            "電商零售", "餐飲服務", "製造業", "新能源", "醫療器材",
            "教育科技", "物流運輸", "綠能環保", "文創媒體", "智慧農業"
        ]
        
        # 台灣地區
        self.regions = [
            "台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市",
            "新竹市", "苗栗縣", "彰化縣", "雲林縣", "嘉義市", "屏東縣"
        ]

    async def connect_db(self):
        """連接資料庫"""
        try:
            await Database.connect()
            self.db = Database.get_database()
            print("✅ 資料庫連接成功")
        except Exception as e:
            print(f"❌ 資料庫連接失敗: {e}")
            raise

    async def clean_all_data(self):
        """清除所有測試資料"""
        print("\n🧹 開始清理現有資料...")
        print("=" * 40)
        
        try:
            # 清除用戶資料
            user_result = await self.db.users.delete_many({})
            print(f"🗑️  清除用戶: {user_result.deleted_count} 筆")
            
            # 清除提案資料（如果存在）
            try:
                proposal_result = await self.db.proposals.delete_many({})
                print(f"🗑️  清除提案: {proposal_result.deleted_count} 筆")
            except:
                print("📝 提案集合不存在（正常）")
            
            # 清除案例資料（如果存在）
            try:
                case_result = await self.db.cases.delete_many({})
                print(f"🗑️  清除案例: {case_result.deleted_count} 筆")
            except:
                print("📝 案例集合不存在（正常）")
                
            print("✅ 資料清理完成")
            
        except Exception as e:
            print(f"❌ 清理資料時發生錯誤: {e}")
            raise

    def generate_admin_data(self) -> List[Dict[str, Any]]:
        """生成管理員資料"""
        admins = [
            {
                "email": "admin@ma-platform.com",
                "password_hash": hash_password("admin123"),
                "role": "admin",
                "first_name": "系統",
                "last_name": "管理員",
                "phone": "+886-2-1234-5678",
                "admin_profile": {
                    "admin_level": "super_admin",
                    "permissions": ["user_management", "proposal_review", "system_config"],
                    "department": "技術部",
                    "employee_id": "ADM001"
                },
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_deleted": False
            },
            {
                "email": "manager@ma-platform.com", 
                "password_hash": hash_password("manager123"),
                "role": "admin",
                "first_name": "平台",
                "last_name": "經理",
                "phone": "+886-2-1234-5679",
                "admin_profile": {
                    "admin_level": "manager",
                    "permissions": ["proposal_review", "user_support"],
                    "department": "營運部",
                    "employee_id": "ADM002"
                },
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_deleted": False
            }
        ]
        return admins

    def generate_buyer_data(self, count: int = 30) -> List[Dict[str, Any]]:
        """生成買方資料"""
        buyers = []
        
        investment_ranges = [
            {"min": 1000000, "max": 5000000, "label": "100萬-500萬"},
            {"min": 5000000, "max": 20000000, "label": "500萬-2000萬"},
            {"min": 20000000, "max": 50000000, "label": "2000萬-5000萬"},
            {"min": 50000000, "max": 100000000, "label": "5000萬-1億"},
            {"min": 100000000, "max": 500000000, "label": "1億以上"}
        ]
        
        for i in range(count):
            company_name = f"{self.fake.company()} {random.choice(['科技', '投資', '創投', '資本', '集團'])}"
            investment_range = random.choice(investment_ranges)
            
            buyer = {
                "email": f"buyer{i+1}@example.com",
                "password_hash": hash_password("buyer123"),
                "role": "buyer",
                "first_name": self.fake.first_name(),
                "last_name": self.fake.last_name(),
                "phone": f"+886-9{random.randint(10000000, 99999999)}",
                "buyer_profile": {
                    "company_info": {
                        "company_name": company_name,
                        "company_description": f"專注於{random.choice(self.industries)}領域的投資公司，擁有豐富的投資經驗和專業團隊。",
                        "established_year": random.randint(1990, 2020),
                        "employee_count": random.randint(10, 500),
                        "website": f"https://www.{company_name.lower().replace(' ', '').replace('科技', 'tech').replace('投資', 'invest')}.com",
                        "address": f"{random.choice(self.regions)}{self.fake.address()}"
                    },
                    "investment_preferences": {
                        "preferred_industries": random.sample(self.industries, random.randint(2, 5)),
                        "investment_stage": random.choice(["early", "growth", "mature", "any"]),
                        "min_investment": investment_range["min"],
                        "max_investment": investment_range["max"],
                        "investment_horizon": random.choice(["short_term", "medium_term", "long_term"]),
                        "geographic_preference": random.sample(self.regions, random.randint(2, 6))
                    },
                    "contact_info": {
                        "primary_contact": self.fake.name(),
                        "contact_title": random.choice(["投資總監", "執行長", "財務長", "投資經理"]),
                        "contact_phone": f"+886-2-{random.randint(20000000, 99999999)}",
                        "contact_email": f"contact@{company_name.lower().replace(' ', '')}.com"
                    },
                    "public_info": {
                        "company_logo": f"https://logo.placeholder.com/{company_name}",
                        "brief_description": f"我們是專業的{random.choice(['創投基金', '私募股權', '策略投資者'])}，尋求優質的投資機會。",
                        "successful_cases_count": random.randint(3, 50),
                        "average_investment_size": (investment_range["min"] + investment_range["max"]) // 2,
                        "decision_timeline": random.choice(["2-4週", "1-2個月", "2-3個月"]),
                        "due_diligence_focus": random.sample([
                            "財務表現", "技術優勢", "市場地位", "管理團隊", "成長潛力", "風險評估"
                        ], random.randint(2, 4))
                    }
                },
                "is_active": True,
                "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 180)),
                "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                "is_deleted": False
            }
            buyers.append(buyer)
        
        return buyers

    def generate_seller_data(self, count: int = 5) -> List[Dict[str, Any]]:
        """生成提案方資料"""
        sellers = []
        
        for i in range(count):
            company_name = f"{self.fake.company()} {random.choice(['科技', '生技', '製造', '服務', '創新'])}"
            revenue = random.randint(5000000, 500000000)  # 500萬到5億
            
            seller = {
                "email": f"seller{i+1}@example.com",
                "password_hash": hash_password("seller123"),
                "role": "seller",
                "first_name": self.fake.first_name(),
                "last_name": self.fake.last_name(),
                "phone": f"+886-9{random.randint(10000000, 99999999)}",
                "seller_profile": {
                    "company_info": {
                        "company_name": company_name,
                        "industry": random.choice(self.industries),
                        "established_year": random.randint(2000, 2020),
                        "employee_count": random.randint(5, 200),
                        "business_model": random.choice(["B2B", "B2C", "B2B2C", "Platform"]),
                        "company_stage": random.choice(["startup", "growth", "mature"]),
                        "location": random.choice(self.regions),
                        "website": f"https://www.{company_name.lower().replace(' ', '')}.com"
                    },
                    "financial_info": {
                        "annual_revenue": revenue,
                        "profit_margin": random.randint(5, 25),
                        "growth_rate": random.randint(-5, 50),
                        "funding_stage": random.choice(["Pre-A", "A輪", "B輪", "C輪", "成熟期"]),
                        "previous_funding": random.randint(0, 100000000),
                        "seeking_amount": random.randint(revenue//10, revenue//2),
                        "valuation": revenue * random.randint(3, 15)
                    },
                    "business_highlights": {
                        "competitive_advantages": random.sample([
                            "技術領先", "市場獨占", "專利保護", "成本優勢", 
                            "品牌知名度", "通路優勢", "人才團隊", "數據資產"
                        ], random.randint(2, 4)),
                        "key_products": [
                            f"產品 {j+1}" for j in range(random.randint(1, 3))
                        ],
                        "target_markets": random.sample(self.regions, random.randint(2, 4)),
                        "major_clients": [
                            f"客戶 {j+1}" for j in range(random.randint(2, 6))
                        ]
                    },
                    "offering_info": {
                        "transaction_type": random.choice(["equity_sale", "asset_sale", "merger", "partnership"]),
                        "seeking_buyer_type": random.choice(["strategic", "financial", "either"]),
                        "timeline": random.choice(["3個月內", "6個月內", "1年內", "彈性"]),
                        "confidentiality_level": random.choice(["high", "medium", "standard"])
                    },
                    "subscription_info": {
                        "plan": "standard",
                        "monthly_proposal_limit": 10,
                        "used_proposals_this_month": random.randint(0, 5),
                        "subscription_start": datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                        "subscription_end": datetime.utcnow() + timedelta(days=random.randint(30, 365))
                    }
                },
                "is_active": True,
                "created_at": datetime.utcnow() - timedelta(days=random.randint(60, 300)),
                "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                "is_deleted": False
            }
            sellers.append(seller)
        
        return sellers

    async def insert_data(self, data: List[Dict], data_type: str) -> bool:
        """插入資料到資料庫"""
        try:
            if data:
                result = await self.db.users.insert_many(data)
                print(f"✅ 成功插入 {len(result.inserted_ids)} 個{data_type}")
                return True
            return False
        except Exception as e:
            print(f"❌ 插入{data_type}失敗: {e}")
            return False

    async def verify_data(self):
        """驗證生成的資料"""
        print("\n🔍 驗證生成的資料...")
        print("=" * 40)
        
        try:
            # 統計各角色用戶數量
            admin_count = await self.db.users.count_documents({"role": "admin"})
            buyer_count = await self.db.users.count_documents({"role": "buyer"}) 
            seller_count = await self.db.users.count_documents({"role": "seller"})
            total_count = await self.db.users.count_documents({})
            
            print(f"👤 管理員數量: {admin_count}")
            print(f"💰 買方數量: {buyer_count}")
            print(f"🏢 提案方數量: {seller_count}")
            print(f"📊 總用戶數量: {total_count}")
            
            # 檢查資料完整性
            incomplete_users = await self.db.users.count_documents({
                "$or": [
                    {"email": {"$exists": False}},
                    {"password": {"$exists": False}},
                    {"role": {"$exists": False}}
                ]
            })
            
            if incomplete_users == 0:
                print("✅ 所有用戶資料完整")
            else:
                print(f"⚠️  發現 {incomplete_users} 個不完整的用戶資料")
                
            # 檢查 Email 重複
            pipeline = [
                {"$group": {"_id": "$email", "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}}
            ]
            duplicates = await self.db.users.aggregate(pipeline).to_list(None)
            
            if not duplicates:
                print("✅ 沒有重複的 Email")
            else:
                print(f"⚠️  發現 {len(duplicates)} 個重複的 Email")
                
        except Exception as e:
            print(f"❌ 驗證資料時發生錯誤: {e}")

    async def show_test_accounts(self):
        """顯示測試帳號資訊"""
        print("\n🔑 測試帳號資訊")
        print("=" * 40)
        print("🔐 **管理員帳號**:")
        print("   📧 admin@ma-platform.com")
        print("   🔒 密碼: admin123")
        print("   👤 角色: 系統管理員")
        print("")
        print("   📧 manager@ma-platform.com")
        print("   🔒 密碼: manager123") 
        print("   👤 角色: 平台經理")
        print("")
        print("💰 **買方測試帳號**:")
        print("   📧 buyer1@example.com")
        print("   🔒 密碼: buyer123")
        print("   📧 buyer2@example.com")
        print("   🔒 密碼: buyer123")
        print("   📧 ... (共30個買方帳號)")
        print("")
        print("🏢 **提案方測試帳號**:")
        print("   📧 seller1@example.com")
        print("   🔒 密碼: seller123")
        print("   📧 seller2@example.com")
        print("   🔒 密碼: seller123")
        print("   📧 ... (共5個提案方帳號)")

    async def run(self):
        """執行清理和重新生成流程"""
        print("🎯 M&A 平台測試資料清理和重新生成")
        print("🔄 適用於 Phase 2 提案管理系統測試")
        print("=" * 50)
        
        try:
            # 1. 連接資料庫
            await self.connect_db()
            
            # 2. 清理現有資料
            await self.clean_all_data()
            
            # 3. 生成新資料
            print("\n🚀 開始生成新的測試資料...")
            print("=" * 40)
            
            admins = self.generate_admin_data()
            buyers = self.generate_buyer_data(30)
            sellers = self.generate_seller_data(5)
            
            # 4. 插入資料庫
            print("\n💾 插入資料到資料庫...")
            print("-" * 30)
            
            admin_success = await self.insert_data(admins, "管理員")
            buyer_success = await self.insert_data(buyers, "買方")
            seller_success = await self.insert_data(sellers, "提案方")
            
            # 5. 驗證資料
            await self.verify_data()
            
            # 6. 顯示測試帳號
            await self.show_test_accounts()
            
            if admin_success and buyer_success and seller_success:
                print("\n🎉 測試資料生成完成！")
                print("🚀 準備開始 Swagger UI 測試！")
                print("\n📋 下一步:")
                print("1. 啟動後端服務: python -m uvicorn app.main:app --reload")
                print("2. 打開 Swagger UI: http://localhost:8000/docs")
                print("3. 使用上述測試帳號登入並測試 API")
            else:
                print("\n❌ 部分資料生成失敗，請檢查錯誤訊息")
                
        except Exception as e:
            print(f"\n❌ 程式執行失敗: {e}")
            sys.exit(1)
        finally:
            await Database.disconnect()


async def main():
    """主函數"""
    generator = DataCleanerAndGenerator()
    await generator.run()


if __name__ == "__main__":
    # 檢查必要的模組
    try:
        import faker
    except ImportError:
        print("❌ 缺少 faker 模組，請安裝:")
        print("pip install faker")
        sys.exit(1)
    
    # 執行程式
    asyncio.run(main())