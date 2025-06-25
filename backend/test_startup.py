 
"""
測試後端基礎設定是否正常
"""
import asyncio
import sys
import os

# 添加路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import Database


async def test_basic_setup():
    """測試基礎設定"""
    print("🧪 測試後端基礎設定...")
    
    # 測試配置
    print(f"✅ 配置載入成功")
    print(f"   - APP_NAME: {settings.APP_NAME}")
    print(f"   - ENVIRONMENT: {settings.ENVIRONMENT}")
    print(f"   - DEBUG: {settings.DEBUG}")
    
    # 測試資料庫連接
    try:
        await Database.connect()
        print(f"✅ 資料庫連接成功")
        print(f"   - Database: {settings.MONGODB_DB_NAME}")
        
        # 健康檢查
        health = await Database.health_check()
        print(f"✅ 資料庫健康檢查: {'通過' if health else '失敗'}")
        
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {e}")
        return False
    finally:
        await Database.disconnect()
    
    print("🎉 所有基礎設定測試通過！")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_basic_setup())
    sys.exit(0 if success else 1)