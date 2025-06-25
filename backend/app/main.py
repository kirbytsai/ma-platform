"""
FastAPI 主應用程式
M&A 平台後端 API 入口點
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import logging

from app.core.config import settings
from app.core.database import Database  # 修復：使用正確的類別匯入
from app.core.exceptions import BusinessException, ValidationException, PermissionDeniedException
from app.api.v1.auth import router as auth_router


# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時執行
    logger.info("🚀 啟動 M&A 平台後端服務...")
    
    # 連接資料庫
    await Database.connect()  # 修復：使用正確的方法名稱
    logger.info("✅ 資料庫連接成功")
    
    yield
    
    # 關閉時執行
    logger.info("🔒 關閉 M&A 平台後端服務...")
    
    # 關閉資料庫連接
    await Database.disconnect()  # 修復：使用正確的方法名稱
    logger.info("✅ 資料庫連接已關閉")


# 建立 FastAPI 應用實例
app = FastAPI(
    title="M&A 平台 API",
    description="""
    ## M&A 平台後端 API

    這是一個企業併購媒合平台的後端 API，支援：

    * **三角色系統**: 管理員、買方、提案方
    * **提案管理**: 完整的提案生命週期
    * **智能媒合**: 買賣方自動配對
    * **安全認證**: JWT Token 認證機制
    * **檔案管理**: 安全的檔案上傳下載

    ### 技術棧
    - **後端框架**: FastAPI + Python 3.11
    - **資料庫**: MongoDB Atlas
    - **認證**: JWT + bcrypt
    - **測試**: pytest + TestClient

    ### 開發階段
    目前處於 MVP 開發階段，專注於核心功能實現。
    """,
    version="1.0.0",
    contact={
        "name": "M&A 平台開發團隊",
        "email": "dev@ma-platform.com",
    },
    license_info={
        "name": "Private License",
    },
    lifespan=lifespan
)


# CORS 中介軟體
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# 請求時間中介軟體
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加請求處理時間標頭"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# 全域異常處理器
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """業務邏輯異常處理"""
    logger.warning(f"Business exception: {exc.message} (Code: {exc.error_code})")
    
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    """資料驗證異常處理"""
    logger.warning(f"Validation exception: {exc.message} (Code: {exc.error_code})")
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(PermissionDeniedException)
async def permission_exception_handler(request: Request, exc: PermissionDeniedException):
    """權限不足異常處理"""
    logger.warning(f"Permission denied: {exc.message} (Code: {exc.error_code})")
    
    return JSONResponse(
        status_code=403,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """FastAPI 請求驗證錯誤處理"""
    logger.warning(f"Request validation error: {exc.errors()}")
    
    # 提取第一個錯誤訊息
    first_error = exc.errors()[0] if exc.errors() else {}
    field = " -> ".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "資料驗證錯誤")
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": f"欄位 '{field}': {message}",
            "error_code": "VALIDATION_ERROR",
            "details": exc.errors(),
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用異常處理"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "伺服器內部錯誤",
            "error_code": "INTERNAL_SERVER_ERROR",
            "timestamp": time.time()
        }
    )


# 根路由
@app.get(
    "/",
    summary="API 根路由",
    description="M&A 平台 API 基本資訊"
)
async def root():
    """API 根路由"""
    return {
        "name": "M&A 平台 API",
        "version": "1.0.0",
        "description": "企業併購媒合平台後端 API",
        "status": "running",
        "timestamp": time.time(),
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }


@app.get(
    "/health",
    summary="健康檢查",
    description="檢查 API 服務和資料庫連接狀態"
)
async def health_check():
    """健康檢查端點"""
    try:
        # 檢查資料庫連接
        health_status = await Database.health_check()  # 修復：使用正確的方法
        
        if health_status:
            return {
                "status": "healthy",
                "service": "M&A Platform API",
                "version": "1.0.0",
                "database": "connected",
                "timestamp": time.time()
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": "M&A Platform API",
                    "version": "1.0.0",
                    "database": "disconnected",
                    "timestamp": time.time()
                }
            )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "M&A Platform API",
                "version": "1.0.0",
                "database": "disconnected",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# API 路由
@app.get(
    "/api",
    summary="API 版本資訊",
    description="取得 API 版本和可用端點資訊"
)
async def api_info():
    """API 版本資訊"""
    return {
        "api_version": "v1",
        "available_endpoints": {
            "authentication": "/api/v1/auth",
            "users": "/api/v1/users (開發中)",
            "proposals": "/api/v1/proposals (開發中)",
            "cases": "/api/v1/cases (開發中)"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "status": "development",
        "current_phase": "Phase 1 - Authentication System",
        "timestamp": time.time()
    }


# 包含認證路由
app.include_router(
    auth_router,
    prefix="/api/v1",
    tags=["認證"]
)


# 開發和測試用端點
@app.get(
    "/api/v1/test/database",
    summary="資料庫連接測試",
    description="測試資料庫連接和基本操作 (開發用)"
)
async def test_database():
    """資料庫連接測試端點"""
    try:
        # 檢查資料庫連接
        db = Database.get_database()  # 修復：使用正確的方法
        
        # 測試基本操作
        await db.command("ping")
        
        # 測試集合操作
        collections = await db.list_collection_names()
        
        # 測試用戶集合
        user_count = await db.users.count_documents({})
        
        return {
            "success": True,
            "message": "資料庫連接正常",
            "database_name": db.name,
            "collections": collections,
            "user_count": user_count,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": f"資料庫連接測試失敗: {str(e)}",
                "error_code": "DATABASE_CONNECTION_ERROR",
                "timestamp": time.time()
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )