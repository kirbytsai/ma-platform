#!/usr/bin/env python3
"""
M&A 平台 Dummy Data 生成腳本
生成完整的測試資料，包含管理員、買方、提案方
支援 Phase 2 提案系統開發所需的豐富測試資料
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
from app.models.user import UserRole


class DummyDataGenerator:
    """Dummy Data 生成器"""
    
    def __init__(self):
        self.fake = Faker(['zh_TW', 'en_US'])  # 支援中英文
        self.db = None
        
        # 行業分類
        self.industries = [
            "科技軟體", "電子製造", "生物科技", "金融服務", "零售電商",
            "餐飲服務", "製造業", "房地產", "醫療健康", "教育培訓",
            "物流運輸", "能源環保", "文創媒體", "農業食品", "旅遊觀光"
        ]
        
        # 地區分類
        self.regions = [
            "台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市",
            "新竹縣市", "苗栗縣", "彰化縣", "雲林縣", "嘉義縣市", "屏東縣",
            "宜蘭縣", "花蓮縣", "台東縣"
        ]
        
        # 公司規模
        self.company_sizes = {
            "微型": {"min": 1, "max": 4},
            "小型": {"min": 5, "max": 29},
            "中型": {"min": 30, "max": 199},
            "大型": {"min": 200, "max": 999},
            "超大型": {"min": 1000, "max": 5000}
        }

    async def connect_db(self):
        """連接資料庫"""
        try:
            await Database.connect()
            self.db = Database.get_database()
            print("✅ 資料庫連接成功")
        except Exception as e:
            print(f"❌ 資料庫連接失敗: {e}")
            sys.exit(1)

    async def clear_existing_data(self):
        """清除現有測試資料 (可選)"""
        try:
            # 注意：這裡可以選擇性清除或保留現有資料
            print("🧹 檢查現有資料...")
            
            user_count = await self.db.users.count_documents({})
            print(f"📊 當前用戶數量: {user_count}")
            
            # 如果要清除所有資料，取消下面的註解
            # await self.db.users.delete_many({})
            # print("🗑️  已清除現有用戶資料")
            
        except Exception as e:
            print(f"❌ 清除資料時發生錯誤: {e}")

    def generate_admin_data(self) -> List[Dict[str, Any]]:
        """生成管理員資料"""
        admins = []
        
        # 系統主管理員
        admin1 = {
            "email": "admin@ma-platform.com",
            "password": hash_password("admin123"),
            "role": UserRole.ADMIN,
            "is_active": True,
            "profile": {
                "full_name": "系統管理員",
                "phone": "+886-2-1234-5678",
                "department": "系統管理部",
                "permissions": ["user_management", "proposal_review", "system_config", "data_export"]
            },
            "created_at": datetime.utcnow() - timedelta(days=365),
            "updated_at": datetime.utcnow()
        }
        
        # 審核管理員
        admin2 = {
            "email": "manager@ma-platform.com",
            "password": hash_password("manager123"),
            "role": UserRole.ADMIN,
            "is_active": True,
            "profile": {
                "full_name": "審核經理",
                "phone": "+886-2-1234-5679",
                "department": "業務審核部",
                "permissions": ["proposal_review", "user_management", "report_view"]
            },
            "created_at": datetime.utcnow() - timedelta(days=300),
            "updated_at": datetime.utcnow()
        }
        
        admins.extend([admin1, admin2])
        return admins

    def generate_buyer_data(self, count: int = 30) -> List[Dict[str, Any]]:
        """生成買方資料"""
        buyers = []
        
        for i in range(1, count + 1):
            # 生成公司基本資料
            company_name = f"{self.fake.company()}集團"
            industry = random.choice(self.industries)
            region = random.choice(self.regions)
            
            # 投資範圍和偏好
            investment_min = random.choice([1000, 5000, 10000, 50000, 100000]) * 10000  # 萬元
            investment_max = investment_min * random.randint(5, 20)
            
            buyer = {
                "email": f"buyer{i}@example.com",
                "password": hash_password("buyer123"),
                "role": UserRole.BUYER,
                "is_active": True,
                "profile": {
                    "full_name": self.fake.name(),
                    "phone": self.fake.phone_number(),
                    "job_title": random.choice(["執行長", "投資總監", "業務發展總監", "策略投資經理", "併購專員"]),
                    "company_info": {
                        "company_name": company_name,
                        "industry": industry,
                        "established_year": random.randint(1980, 2020),
                        "headquarters": region,
                        "website": f"https://www.{company_name.replace('集團', '').lower()}.com.tw",
                        "description": f"專注於{industry}領域的投資集團，擁有豐富的併購整合經驗。"
                    }
                },
                "buyer_profile": {
                    # 公開頁面資訊
                    "public_profile": {
                        "investment_focus": random.choice([
                            "科技創新企業", "傳統產業升級", "新創事業", "穩定獲利企業", "高成長潛力"
                        ]),
                        "investment_range": {
                            "min_amount": investment_min,
                            "max_amount": investment_max,
                            "currency": "TWD"
                        },
                        "preferred_industries": random.sample(self.industries, random.randint(3, 6)),
                        "geographic_focus": random.sample(self.regions, random.randint(2, 5)),
                        "investment_criteria": {
                            "min_annual_revenue": investment_min // 10,
                            "preferred_company_age": random.randint(3, 15),
                            "growth_rate_requirement": random.randint(10, 50),
                            "profit_margin_requirement": random.randint(5, 20)
                        },
                        "portfolio_highlights": [
                            f"成功投資{random.randint(5, 50)}家企業",
                            f"累計投資金額超過{random.randint(10, 100)}億元",
                            f"平均年化報酬率{random.randint(15, 35)}%"
                        ]
                    },
                    # 私人設定
                    "preferences": {
                        "notification_email": True,
                        "public_profile_visible": True,
                        "auto_response": random.choice([True, False]),
                        "preferred_contact_time": random.choice(["上午", "下午", "不限"])
                    },
                    "investment_history": {
                        "total_investments": random.randint(3, 25),
                        "successful_exits": random.randint(1, 10),
                        "current_portfolio_size": random.randint(5, 30)
                    }
                },
                "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 300)),
                "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 30))
            }
            
            buyers.append(buyer)
        
        return buyers

    def generate_seller_data(self, count: int = 5) -> List[Dict[str, Any]]:
        """生成提案方資料"""
        sellers = []
        
        for i in range(1, count + 1):
            # 生成公司詳細資料
            company_name = f"{self.fake.company()}有限公司"
            industry = random.choice(self.industries)
            region = random.choice(self.regions)
            size_category = random.choice(list(self.company_sizes.keys()))
            employee_count = random.randint(
                self.company_sizes[size_category]["min"],
                self.company_sizes[size_category]["max"]
            )
            
            # 財務數據生成
            annual_revenue = employee_count * random.randint(800, 2000) * 1000  # 每員工年產值
            profit_margin = random.randint(5, 25)
            net_profit = annual_revenue * profit_margin // 100
            
            seller = {
                "email": f"seller{i}@example.com",
                "password": hash_password("seller123"),
                "role": UserRole.SELLER,
                "is_active": True,
                "profile": {
                    "full_name": self.fake.name(),
                    "phone": self.fake.phone_number(),
                    "job_title": random.choice(["執行長", "創辦人", "總經理", "董事長", "營運長"]),
                    "company_info": {
                        "company_name": company_name,
                        "industry": industry,
                        "established_year": random.randint(2000, 2020),
                        "headquarters": region,
                        "employee_count": employee_count,
                        "website": f"https://www.{company_name.replace('有限公司', '').lower()}.com",
                        "registration_number": f"5{random.randint(1000000, 9999999)}",
                        "description": f"成立於{random.randint(2000, 2020)}年的{industry}企業，專注於{random.choice(['創新技術', '優質服務', '製造精良', '市場開拓'])}。"
                    }
                },
                "seller_profile": {
                    # 詳細公司資料
                    "business_info": {
                        "business_model": random.choice([
                            "B2B 服務", "B2C 零售", "B2B2C 平台", "製造代工", "技術授權"
                        ]),
                        "main_products": [
                            f"{industry}相關產品A", f"{industry}相關產品B", f"{industry}相關服務"
                        ],
                        "target_market": random.sample(self.regions, random.randint(2, 4)),
                        "competitive_advantages": [
                            "技術領先", "成本優勢", "通路廣泛", "品牌知名度", "客戶忠誠度"
                        ][:random.randint(2, 4)]
                    },
                    "financial_overview": {
                        "annual_revenue": annual_revenue,
                        "net_profit": net_profit,
                        "profit_margin": profit_margin,
                        "growth_rate": random.randint(-5, 50),
                        "debt_ratio": random.randint(10, 60),
                        "cash_flow": random.choice(["正向", "持平", "略負"])
                    },
                    "operational_data": {
                        "monthly_active_customers": random.randint(100, 10000),
                        "customer_retention_rate": random.randint(70, 95),
                        "average_order_value": random.randint(500, 50000),
                        "inventory_turnover": random.randint(4, 12)
                    },
                    "team_info": {
                        "management_team_size": random.randint(3, 8),
                        "rd_team_size": random.randint(2, 20),
                        "sales_team_size": random.randint(3, 15),
                        "key_personnel_tenure": random.randint(2, 10)
                    }
                },
                "created_at": datetime.utcnow() - timedelta(days=random.randint(60, 400)),
                "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 60))
            }
            
            sellers.append(seller)
        
        return sellers

    async def insert_users(self, users: List[Dict[str, Any]], user_type: str):
        """批量插入用戶資料"""
        try:
            if users:
                result = await self.db.users.insert_many(users)
                print(f"✅ 成功插入 {len(result.inserted_ids)} 個{user_type}")
                return True
        except Exception as e:
            print(f"❌ 插入{user_type}時發生錯誤: {e}")
            return False

    async def generate_and_insert_all(self):
        """生成並插入所有測試資料"""
        print("🚀 開始生成 M&A 平台測試資料...")
        print("=" * 50)
        
        # 生成各類用戶資料
        print("📋 生成管理員資料...")
        admins = self.generate_admin_data()
        
        print("📋 生成買方資料...")
        buyers = self.generate_buyer_data(30)
        
        print("📋 生成提案方資料...")
        sellers = self.generate_seller_data(5)
        
        # 插入資料庫
        print("\n💾 插入資料庫...")
        print("-" * 30)
        
        admin_success = await self.insert_users(admins, "管理員")
        buyer_success = await self.insert_users(buyers, "買方")
        seller_success = await self.insert_users(sellers, "提案方")
        
        # 統計結果
        print("\n📊 資料生成統計:")
        print("=" * 30)
        if admin_success:
            print(f"👤 管理員: {len(admins)} 個")
        if buyer_success:
            print(f"💰 買方: {len(buyers)} 個")
        if seller_success:
            print(f"🏢 提案方: {len(sellers)} 個")
        
        total_users = len(admins) + len(buyers) + len(sellers)
        print(f"📈 總計用戶: {total_users} 個")
        
        # 顯示測試帳號資訊
        print("\n🔑 測試帳號資訊:")
        print("=" * 30)
        print("管理員帳號:")
        print("  📧 admin@ma-platform.com / admin123")
        print("  📧 manager@ma-platform.com / manager123")
        print("\n買方測試帳號:")
        print("  📧 buyer1@example.com / buyer123")
        print("  📧 buyer2@example.com / buyer123")
        print("  📧 ... (共30個)")
        print("\n提案方測試帳號:")
        print("  📧 seller1@example.com / seller123")
        print("  📧 seller2@example.com / seller123")
        print("  📧 ... (共5個)")

    async def verify_data(self):
        """驗證生成的資料"""
        print("\n🔍 驗證生成的資料...")
        print("-" * 30)
        
        try:
            # 統計各角色用戶數量
            admin_count = await self.db.users.count_documents({"role": "admin"})
            buyer_count = await self.db.users.count_documents({"role": "buyer"})
            seller_count = await self.db.users.count_documents({"role": "seller"})
            total_count = await self.db.users.count_documents({})
            
            print(f"✅ 管理員數量: {admin_count}")
            print(f"✅ 買方數量: {buyer_count}")
            print(f"✅ 提案方數量: {seller_count}")
            print(f"✅ 總用戶數量: {total_count}")
            
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
                
        except Exception as e:
            print(f"❌ 驗證資料時發生錯誤: {e}")


async def main():
    """主函數"""
    print("🎯 M&A 平台 Dummy Data 生成器")
    print("💫 Phase 2 開發專用測試資料")
    print("=" * 50)
    
    generator = DummyDataGenerator()
    
    try:
        # 連接資料庫
        await generator.connect_db()
        
        # 清除現有資料 (可選)
        await generator.clear_existing_data()
        
        # 生成並插入測試資料
        await generator.generate_and_insert_all()
        
        # 驗證生成的資料
        await generator.verify_data()
        
        print("\n🎉 測試資料生成完成！")
        print("🚀 準備開始 Phase 2 提案系統開發！")
        
    except Exception as e:
        print(f"❌ 程式執行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 檢查依賴
    try:
        import faker
    except ImportError:
        print("❌ 缺少 faker 依賴，請安裝:")
        print("pip install faker")
        sys.exit(1)
    
    # 執行主程式
    asyncio.run(main())