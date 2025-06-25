"""
生成用戶 Dummy Data
"""
import asyncio
import sys
import os
from datetime import datetime
from faker import Faker

# 添加上層目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Database
from app.core.security import hash_password

fake = Faker(['zh_TW', 'en_US'])


async def generate_admin_users():
    """生成管理員用戶"""
    admin_users = [
        {
            "email": "admin@ma-platform.com",
            "password": hash_password("admin123"),
            "role": "admin",
            "profile": {
                "full_name": "系統管理員",
                "phone": "+886-2-1234-5678",
                "company": "M&A Platform"
            },
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        },
        {
            "email": "manager@ma-platform.com",
            "password": hash_password("manager123"),
            "role": "admin",
            "profile": {
                "full_name": "平台經理",
                "phone": "+886-2-1234-5679",
                "company": "M&A Platform"
            },
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
    ]
    
    return admin_users


async def generate_buyer_users(count: int = 30):
    """生成買方用戶"""
    buyers = []
    
    industries = [
        "科技", "製造業", "金融服務", "零售", "醫療保健", 
        "房地產", "能源", "電信", "媒體", "教育"
    ]
    
    investment_ranges = [
        {"min": 1000000, "max": 5000000},
        {"min": 5000000, "max": 10000000},
        {"min": 10000000, "max": 50000000},
        {"min": 50000000, "max": 100000000},
        {"min": 100000000, "max": 500000000}
    ]
    
    for i in range(count):
        company_name = fake.company()
        
        buyer = {
            "email": f"buyer{i+1}@{fake.domain_name()}",
            "password": hash_password("buyer123"),
            "role": "buyer",
            "profile": {
                "full_name": fake.name(),
                "phone": fake.phone_number(),
                "company": company_name
            },
            "buyer_profile": {
                "company_name": company_name,
                "investment_focus": fake.text(max_nb_chars=200),
                "investment_range": fake.random_element(investment_ranges),
                "preferred_industries": fake.random_elements(
                    industries, 
                    length=fake.random_int(2, 4)
                ),
                "geographic_focus": fake.random_elements([
                    "台灣", "中國大陸", "東南亞", "日本", "韓國", "美國", "歐洲"
                ], length=fake.random_int(1, 3)),
                "investment_criteria": fake.text(max_nb_chars=300),
                "portfolio_highlights": [
                    fake.company() for _ in range(fake.random_int(2, 5))
                ],
                "is_public": True
            },
            "is_active": True,
            "created_at": fake.date_time_between(start_date='-1y', end_date='now'),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        
        buyers.append(buyer)
    
    return buyers


async def generate_seller_users(count: int = 5):
    """生成提案方用戶"""
    sellers = []
    
    for i in range(count):
        company_name = fake.company()
        
        seller = {
            "email": f"seller{i+1}@{fake.domain_name()}",
            "password": hash_password("seller123"),
            "role": "seller",
            "profile": {
                "full_name": fake.name(),
                "phone": fake.phone_number(),
                "company": company_name
            },
            "seller_profile": {
                "company_name": company_name,
                "company_registration": fake.random_number(digits=8),
                "contact_person": fake.name(),
                "contact_title": fake.random_element([
                    "執行長", "財務長", "投資關係主管", "業務總監"
                ]),
                "subscription_plan": "basic",
                "monthly_proposal_limit": 3,
                "used_proposals_this_month": 0
            },
            "is_active": True,
            "created_at": fake.date_time_between(start_date='-6m', end_date='now'),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        
        sellers.append(seller)
    
    return sellers


async def main():
    """主函數"""
    try:
        # 連接資料庫
        await Database.connect()
        db = Database.get_database()
        
        print(f"✅ 已生成 {len(seller_users)} 個提案方用戶")
        
        print(f"🎉 用戶 Dummy Data 生成完成！")
        print(f"總計: {len(admin_users) + len(buyer_users) + len(seller_users)} 個用戶")
        print("\n📋 測試帳號:")
        print("管理員: admin@ma-platform.com / admin123")
        print("管理員: manager@ma-platform.com / manager123")
        print("買方: buyer1@example.com / buyer123")
        print("提案方: seller1@example.com / seller123")
        
    except Exception as e:
        print(f"❌ 生成過程中發生錯誤: {e}")
        raise
    finally:
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())("🚀 開始生成用戶 Dummy Data...")
        
        # 清空現有用戶資料
        await db.users.delete_many({})
        print("🧹 已清空現有用戶資料")
        
        # 生成管理員
        admin_users = await generate_admin_users()
        await db.users.insert_many(admin_users)
        print(f"✅ 已生成 {len(admin_users)} 個管理員用戶")
        
        # 生成買方
        buyer_users = await generate_buyer_users(30)
        await db.users.insert_many(buyer_users)
        print(f"✅ 已生成 {len(buyer_users)} 個買方用戶")
        
        # 生成提案方
        seller_users = await generate_seller_users(5)
        await db.users.insert_many(seller_users)
        print(f"✅ 已生成 {len(seller_users)} 個提案方用戶")
        
        print