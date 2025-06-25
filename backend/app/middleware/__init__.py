 
"""
自定義中介軟體
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """請求日誌中介軟體"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # 記錄請求開始
        logger.info(f"📥 {request.method} {request.url}")
        
        # 執行請求
        response = await call_next(request)
        
        # 計算處理時間
        process_time = time.time() - start_time
        
        # 記錄請求結束
        logger.info(
            f"📤 {request.method} {request.url} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        # 添加處理時間到響應頭
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """錯誤處理中介軟體"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # 記錄未處理的異常
            logger.error(f"未處理的異常: {str(e)}", exc_info=True)
            
            # 返回通用錯誤響應
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "內部伺服器錯誤",
                        "details": None
                    }
                }
            )