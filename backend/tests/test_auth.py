"""
認證系統測試
測試用戶註冊、登入、Token 管理等功能
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.models.user import UserRole
from app.services.auth_service import auth_service
from app.services.user_service import user_service
from app.core.database import get_database


class TestAuthSystem:
    """認證系統測試類"""
    
    @pytest.fixture(scope="class")
    def event_loop(self):
        """建立事件循環"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    @pytest.fixture(scope="class")
    async def setup_database(self):
        """設定測試資料庫"""
        # 清理測試資料
        db = await get_database()
        await db.users.delete_many({"email": {"$regex": "test.*@example.com"}})
        yield
        # 測試後清理
        await db.users.delete_many({"email": {"$regex": "test.*@example.com"}})
    
    @pytest.fixture
    def client(self):
        """建立測試客戶端"""
        return TestClient(app)
    
    @pytest.fixture
    async def test_user_data(self):
        """測試用戶資料"""
        return {
            "buyer": {
                "email": "test.buyer@example.com",
                "password": "testpassword123",
                "role": "buyer",
                "first_name": "測試",
                "last_name": "買方",
                "phone": "+886-912-345-678"
            },
            "seller": {
                "email": "test.seller@example.com",
                "password": "testpassword123",
                "role": "seller",
                "first_name": "測試",
                "last_name": "賣方",
                "phone": "+886-987-654-321"
            }
        }


class TestUserRegistration(TestAuthSystem):
    """用戶註冊測試"""
    
    @pytest.mark.asyncio
    async def test_buyer_registration_success(self, client, test_user_data, setup_database):
        """測試買方註冊成功"""
        buyer_data = test_user_data["buyer"].copy()
        buyer_data["confirm_password"] = buyer_data["password"]
        
        response = client.post("/api/v1/auth/register", json=buyer_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "註冊成功"
        assert "user" in data
        assert "tokens" in data
        
        # 檢查用戶資料
        user = data["user"]
        assert user["email"] == buyer_data["email"]
        assert user["role"] == "buyer"
        assert user["first_name"] == buyer_data["first_name"]
        assert user["is_active"] == True
        assert "password_hash" not in user  # 不應包含敏感資料
        
        # 檢查 Token
        tokens = data["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0
    
    @pytest.mark.asyncio
    async def test_seller_registration_success(self, client, test_user_data, setup_database):
        """測試提案方註冊成功"""
        seller_data = test_user_data["seller"].copy()
        seller_data["confirm_password"] = seller_data["password"]
        
        response = client.post("/api/v1/auth/register", json=seller_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] == True
        assert data["user"]["role"] == "seller"
        assert "tokens" in data
    
    @pytest.mark.asyncio
    async def test_registration_with_profile_data(self, client, setup_database):
        """測試帶初始資料的註冊"""
        registration_data = {
            "email": "test.buyer.profile@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123",
            "role": "buyer",
            "first_name": "測試",
            "last_name": "買方",
            "buyer_profile": {
                "company_name": "測試創投",
                "investment_focus": ["technology"],
                "geographic_focus": "Asia"
            }
        }
        
        response = client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] == True
        assert data["user"]["buyer_profile"]["company_name"] == "測試創投"
    
    @pytest.mark.asyncio
    async def test_registration_duplicate_email(self, client, test_user_data, setup_database):
        """測試重複 email 註冊"""
        buyer_data = test_user_data["buyer"].copy()
        buyer_data["confirm_password"] = buyer_data["password"]
        
        # 第一次註冊
        response1 = client.post("/api/v1/auth/register", json=buyer_data)
        assert response1.status_code == 201
        
        # 第二次註冊 (重複 email)
        response2 = client.post("/api/v1/auth/register", json=buyer_data)
        assert response2.status_code == 409
        
        data = response2.json()
        assert data["success"] == False
        assert "已被註冊" in data["message"]
    
    @pytest.mark.asyncio
    async def test_registration_password_mismatch(self, client, test_user_data):
        """測試密碼不一致"""
        buyer_data = test_user_data["buyer"].copy()
        buyer_data["confirm_password"] = "different_password"
        
        response = client.post("/api/v1/auth/register", json=buyer_data)
        
        assert response.status_code == 422
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_registration_admin_forbidden(self, client):
        """測試管理員註冊被禁止"""
        admin_data = {
            "email": "test.admin@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123",
            "role": "admin",
            "first_name": "測試",
            "last_name": "管理員"
        }
        
        response = client.post("/api/v1/auth/register", json=admin_data)
        
        assert response.status_code == 403
        data = response.json()
        assert data["success"] == False
        assert "管理員" in data["message"]


class TestUserLogin(TestAuthSystem):
    """用戶登入測試"""
    
    @pytest.fixture(scope="class")
    async def create_test_users(self, setup_database):
        """建立測試用戶"""
        # 建立買方測試用戶
        buyer = await user_service.create_user(
            email="login.buyer@example.com",
            password="testpassword123",
            role=UserRole.BUYER,
            first_name="登入",
            last_name="買方"
        )
        
        # 建立已停用的用戶
        inactive_user = await user_service.create_user(
            email="inactive.user@example.com",
            password="testpassword123",
            role=UserRole.SELLER,
            first_name="停用",
            last_name="用戶"
        )
        await user_service.deactivate_user(inactive_user.id)
        
        return {"buyer": buyer, "inactive": inactive_user}
    
    @pytest.mark.asyncio
    async def test_login_success(self, client, create_test_users):
        """測試登入成功"""
        login_data = {
            "email": "login.buyer@example.com",
            "password": "testpassword123",
            "remember_me": False
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "登入成功"
        assert "user" in data
        assert "tokens" in data
        
        # 檢查用戶資料
        user = data["user"]
        assert user["email"] == login_data["email"]
        assert user["role"] == "buyer"
        
        # 檢查 Token
        tokens = data["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
    
    @pytest.mark.asyncio
    async def test_login_remember_me(self, client, create_test_users):
        """測試記住我登入"""
        login_data = {
            "email": "login.buyer@example.com",
            "password": "testpassword123",
            "remember_me": True
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # 記住我應該有更長的有效期
        tokens = data["tokens"]
        assert tokens["expires_in"] > 86400  # 超過 24 小時
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """測試無效憑證"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
            "remember_me": False
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, create_test_users):
        """測試錯誤密碼"""
        login_data = {
            "email": "login.buyer@example.com",
            "password": "wrongpassword",
            "remember_me": False
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_login_inactive_account(self, client, create_test_users):
        """測試停用帳號登入"""
        login_data = {
            "email": "inactive.user@example.com",
            "password": "testpassword123",
            "remember_me": False
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 403
        data = response.json()
        assert data["success"] == False
        assert "停用" in data["message"]


class TestTokenManagement(TestAuthSystem):
    """Token 管理測試"""
    
    @pytest.fixture
    async def authenticated_user(self, client):
        """建立已認證用戶"""
        # 註冊用戶
        register_data = {
            "email": "token.test@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123",
            "role": "buyer",
            "first_name": "Token",
            "last_name": "測試"
        }
        
        register_response = client.post("/api/v1/auth/register", json=register_data)
        return register_response.json()
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client, authenticated_user):
        """測試取得當前用戶"""
        tokens = authenticated_user["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "token.test@example.com"
        assert data["role"] == "buyer"
        assert "password_hash" not in data
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client):
        """測試無效 Token"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client):
        """測試未提供 Token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client, authenticated_user):
        """測試 Token 刷新"""
        tokens = authenticated_user["tokens"]
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        
        # 新 Token 應該不同
        assert data["access_token"] != tokens["access_token"]
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client):
        """測試無效 Refresh Token"""
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_logout(self, client, authenticated_user):
        """測試登出"""
        tokens = authenticated_user["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        logout_data = {"refresh_token": tokens["refresh_token"]}
        
        response = client.post("/api/v1/auth/logout", json=logout_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "登出成功"
        
        # 登出後 Refresh Token 應該無效
        refresh_response = client.post("/api/v1/auth/refresh", json=logout_data)
        assert refresh_response.status_code == 401


class TestPasswordManagement(TestAuthSystem):
    """密碼管理測試"""
    
    @pytest.fixture
    async def user_for_password_test(self, client):
        """建立用於密碼測試的用戶"""
        register_data = {
            "email": "password.test@example.com",
            "password": "oldpassword123",
            "confirm_password": "oldpassword123",
            "role": "seller",
            "first_name": "密碼",
            "last_name": "測試"
        }
        
        register_response = client.post("/api/v1/auth/register", json=register_data)
        return register_response.json()
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, client, user_for_password_test):
        """測試密碼修改成功"""
        tokens = user_for_password_test["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        password_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
            "confirm_new_password": "newpassword456"
        }
        
        response = client.put("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "密碼修改成功"
        
        # 用新密碼登入測試
        login_data = {
            "email": "password.test@example.com",
            "password": "newpassword456"
        }
        
        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client, user_for_password_test):
        """測試錯誤的當前密碼"""
        tokens = user_for_password_test["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword456",
            "confirm_new_password": "newpassword456"
        }
        
        response = client.put("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, client, user_for_password_test):
        """測試新密碼不一致"""
        tokens = user_for_password_test["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        password_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
            "confirm_new_password": "differentpassword"
        }
        
        response = client.put("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 422  # Pydantic 驗證錯誤


class TestAuthEndpoints(TestAuthSystem):
    """認證端點測試"""
    
    @pytest.mark.asyncio
    async def test_auth_test_endpoint(self, client):
        """測試認證測試端點"""
        response = client.get("/api/v1/auth/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_protected_test_endpoint(self, client, authenticated_user):
        """測試受保護的測試端點"""
        tokens = authenticated_user["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        response = client.get("/api/v1/auth/protected-test", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "user_id" in data
        assert "user_email" in data
        assert "user_role" in data
    
    @pytest.mark.asyncio
    async def test_protected_test_endpoint_unauthorized(self, client):
        """測試受保護端點未授權訪問"""
        response = client.get("/api/v1/auth/protected-test")
        
        assert response.status_code == 401


# 執行測試命令示例
"""
執行所有認證測試:
pytest tests/test_auth.py -v

執行特定測試類:
pytest tests/test_auth.py::TestUserRegistration -v

執行特定測試方法:
pytest tests/test_auth.py::TestUserLogin::test_login_success -v

包含測試覆蓋率:
pytest tests/test_auth.py --cov=app.services.auth_service --cov=app.api.v1.auth
""""""
認證系統測試
測試用戶註冊、登入、Token 管理等功能
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.models.user import UserRole
from app.services.auth_service import auth_service
from app.services.user_service import user_service
from app.core.database import get_database


class TestAuthSystem:
    """認證系統測試類"""
    
    @pytest.fixture(scope="class")
    def event_loop(self):
        """建立事件循環"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    @pytest.fixture(scope="class")
    async def setup_database(self):
        """設定測試資料庫"""
        # 清理測試資料
        db = await get_database()
        await db.users.delete_many({"email": {"$regex": "test.*@example.com"}})
        yield
        # 測試後清理
        await db.users.delete_many({"email": {"$regex": "test.*@example.com"}})
    
    @pytest.fixture
    def client(self):
        """建立測試客戶端"""
        return TestClient(app)
    
    @pytest.fixture
    async def test_user_data(self):
        """測試用戶資料"""
        return {
            "buyer": {
                "email": "test.buyer@example.com",
                "password": "testpassword123",
                "role": "buyer",
                "first_name": "測試",
                "last_name": "買方",
                "phone": "+886-912-345-678"
            },
            "seller": {
                "email": "test.seller@example.com",
                "password": "testpassword123",
                "role": "seller",
                "first_name": "測試",
                "last_name": "賣方",
                "phone": "+886-987-654-321"
            }
        }


class TestUserRegistration(TestAuthSystem):
    """用戶註冊測試"""
    
    @pytest.mark.asyncio
    async def test_buyer_registration_success(self, client, test_user_data, setup_database):
        """測試買方註冊成功"""
        buyer_data = test_user_data["buyer"].copy()
        buyer_data["confirm_password"] = buyer_data["password"]
        
        response = client.post("/api/v1/auth/register", json=buyer_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "註冊成功"
        assert "user" in data
        assert "tokens" in data
        
        # 檢查用戶資料
        user = data["user"]
        assert user["email"] == buyer_data["email"]
        assert user["role"] == "buyer"
        assert user["first_name"] == buyer_data["first_name"]
        assert user["is_active"] == True
        assert "password_hash" not in user  # 不應包含敏感資料
        
        # 檢查 Token
        tokens = data["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0
    
    @pytest.mark.asyncio
    async def test_seller_registration_success(self, client, test_user_data, setup_database):
        """測試提案方註冊成功"""
        seller_data = test_user_data["seller"].copy()
        seller_data["confirm_password"] = seller_data["password"]
        
        response = client.post("/api/v1/auth/register", json=seller_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] == True
        assert data["user"]["role"] == "seller"
        assert "tokens" in data
    
    @pytest.mark.asyncio
    async def test_registration_with_profile_data(self, client, setup_database):
        """測試帶初始資料的註冊"""
        registration_data = {
            "email": "test.buyer.profile@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123",
            "role": "buyer",
            "first_name": "測試",
            "last_name": "買方",
            "buyer_profile": {
                "company_name": "測試創投",
                "investment_focus": ["technology"],
                "geographic_focus": "Asia"
            }
        }
        
        response = client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] == True
        assert data["user"]["buyer_profile"]["company_name"] == "測試創投"
    
    @pytest.mark.asyncio
    async def test_registration_duplicate_email(self, client, test_user_data, setup_database):
        """測試重複 email 註冊"""
        buyer_data = test_user_data["buyer"].copy()
        buyer_data["confirm_password"] = buyer_data["password"]
        
        # 第一次註冊
        response1 = client.post("/api/v1/auth/register", json=buyer_data)
        assert response1.status_code == 201
        
        # 第二次註冊 (重複 email)
        response2 = client.post("/api/v1/auth/register", json=buyer_data)
        assert response2.status_code == 409
        
        data = response2.json()
        assert data["success"] == False
        assert "已被註冊" in data["message"]
    
    @pytest.mark.asyncio
    async def test_registration_password_mismatch(self, client, test_user_data):
        """測試密碼不一致"""
        buyer_data = test_user_data["buyer"].copy()
        buyer_data["confirm_password"] = "different_password"
        
        response = client.post("/api/v1/auth/register", json=buyer_data)
        
        assert response.status_code == 422
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_registration_admin_forbidden(self, client):
        """測試管理員註冊被禁止"""
        admin_data = {
            "email": "test.admin@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123",
            "role": "admin",
            "first_name": "測試",
            "last_name": "管理員"
        }
        
        response = client.post("/api/v1/auth/register", json=admin_data)
        
        assert response.status_code == 403
        data = response.json()
        assert data["success"] == False
        assert "管理員" in data["message"]


class TestUserLogin(TestAuthSystem):
    """用戶登入測試"""
    
    @pytest.fixture(scope="class")
    async def create_test_users(self, setup_database):
        """建立測試用戶"""
        # 建立買方測試用戶
        buyer = await user_service.create_user(
            email="login.buyer@example.com",
            password="testpassword123",
            role=UserRole.BUYER,
            first_name="登入",
            last_name="買方"
        )
        
        # 建立已停用的用戶
        inactive_user = await user_service.create_user(
            email="inactive.user@example.com",
            password="testpassword123",
            role=UserRole.SELLER,
            first_name="停用",
            last_name="用戶"
        )
        await user_service.deactivate_user(inactive_user.id)
        
        return {"buyer": buyer, "inactive": inactive_user}
    
    @pytest.mark.asyncio
    async def test_login_success(self, client, create_test_users):
        """測試登入成功"""
        login_data = {
            "email": "login.buyer@example.com",
            "password": "testpassword123",
            "remember_me": False
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "登入成功"
        assert "user" in data
        assert "tokens" in data
        
        # 檢查用戶資料
        user = data["user"]
        assert user["email"] == login_data["email"]
        assert user["role"] == "buyer"
        
        # 檢查 Token
        tokens = data["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
    
    @pytest.mark.asyncio
    async def test_login_remember_me(self, client, create_test_users):
        """測試記住我登入"""
        login_data = {
            "email": "login.buyer@example.com",
            "password": "testpassword123",
            "remember_me": True
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # 記住我應該有更長的有效期
        tokens = data["tokens"]
        assert tokens["expires_in"] > 86400  # 超過 24 小時
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """測試無效憑證"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
            "remember_me": False
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, create_test_users):
        """測試錯誤密碼"""
        login_data = {
            "email": "login.buyer@example.com",
            "password": "wrongpassword",
            "remember_me": False
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_login_inactive_account(self, client, create_test_users):
        """測試停用帳號登入"""
        login_data = {
            "email": "inactive.user@example.com",
            "password": "testpassword123",
            "remember_me": False
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 403
        data = response.json()
        assert data["success"] == False
        assert "停用" in data["message"]


class TestTokenManagement(TestAuthSystem):
    """Token 管理測試"""
    
    @pytest.fixture
    async def authenticated_user(self, client):
        """建立已認證用戶"""
        # 註冊用戶
        register_data = {
            "email": "token.test@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123",
            "role": "buyer",
            "first_name": "Token",
            "last_name": "測試"
        }
        
        register_response = client.post("/api/v1/auth/register", json=register_data)
        return register_response.json()
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client, authenticated_user):
        """測試取得當前用戶"""
        tokens = authenticated_user["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "token.test@example.com"
        assert data["role"] == "buyer"
        assert "password_hash" not in data
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client):
        """測試無效 Token"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client):
        """測試未提供 Token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client, authenticated_user):
        """測試 Token 刷新"""
        tokens = authenticated_user["tokens"]
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        
        # 新 Token 應該不同
        assert data["access_token"] != tokens["access_token"]
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client):
        """測試無效 Refresh Token"""
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_logout(self, client, authenticated_user):
        """測試登出"""
        tokens = authenticated_user["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        logout_data = {"refresh_token": tokens["refresh_token"]}
        
        response = client.post("/api/v1/auth/logout", json=logout_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "登出成功"
        
        # 登出後 Refresh Token 應該無效
        refresh_response = client.post("/api/v1/auth/refresh", json=logout_data)
        assert refresh_response.status_code == 401


class TestPasswordManagement(TestAuthSystem):
    """密碼管理測試"""
    
    @pytest.fixture
    async def user_for_password_test(self, client):
        """建立用於密碼測試的用戶"""
        register_data = {
            "email": "password.test@example.com",
            "password": "oldpassword123",
            "confirm_password": "oldpassword123",
            "role": "seller",
            "first_name": "密碼",
            "last_name": "測試"
        }
        
        register_response = client.post("/api/v1/auth/register", json=register_data)
        return register_response.json()
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, client, user_for_password_test):
        """測試密碼修改成功"""
        tokens = user_for_password_test["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        password_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
            "confirm_new_password": "newpassword456"
        }
        
        response = client.put("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "密碼修改成功"
        
        # 用新密碼登入測試
        login_data = {
            "email": "password.test@example.com",
            "password": "newpassword456"
        }
        
        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client, user_for_password_test):
        """測試錯誤的當前密碼"""
        tokens = user_for_password_test["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword456",
            "confirm_new_password": "newpassword456"
        }
        
        response = client.put("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] == False
    
    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, client, user_for_password_test):
        """測試新密碼不一致"""
        tokens = user_for_password_test["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        password_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
            "confirm_new_password": "differentpassword"
        }
        
        response = client.put("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 422  # Pydantic 驗證錯誤


class TestAuthEndpoints(TestAuthSystem):
    """認證端點測試"""
    
    @pytest.mark.asyncio
    async def test_auth_test_endpoint(self, client):
        """測試認證測試端點"""
        response = client.get("/api/v1/auth/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_protected_test_endpoint(self, client, authenticated_user):
        """測試受保護的測試端點"""
        tokens = authenticated_user["tokens"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        response = client.get("/api/v1/auth/protected-test", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "user_id" in data
        assert "user_email" in data
        assert "user_role" in data
    
    @pytest.mark.asyncio
    async def test_protected_test_endpoint_unauthorized(self, client):
        """測試受保護端點未授權訪問"""
        response = client.get("/api/v1/auth/protected-test")
        
        assert response.status_code == 401


# 執行測試命令示例
"""
執行所有認證測試:
pytest tests/test_auth.py -v

執行特定測試類:
pytest tests/test_auth.py::TestUserRegistration -v

執行特定測試方法:
pytest tests/test_auth.py::TestUserLogin::test_login_success -v

包含測試覆蓋率:
pytest tests/test_auth.py --cov=app.services.auth_service --cov=app.api.v1.auth
"""