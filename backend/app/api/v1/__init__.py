 
"""
API v1 路由模組初始化
暫時建立空的路由，後續會逐步實現
"""
# from fastapi import APIRouter
# from app.models.base import BaseResponse

# # 建立空的路由器
# def create_empty_router(name: str) -> APIRouter:
#     """建立空的路由器"""
#     router = APIRouter()
    
#     @router.get("/")
#     async def placeholder():
#         return BaseResponse(
#             success=True,
#             message=f"{name} API 開發中",
#             data={"status": "coming_soon"}
#         )
    
#     return router

# # 暫時的空路由器
# users = create_empty_router("用戶管理")
# proposals = create_empty_router("提案管理") 
# cases = create_empty_router("案例管理")
# buyers = create_empty_router("買方系統")
# admin = create_empty_router("管理員功能")
# messages = create_empty_router("訊息系統")
# notifications = create_empty_router("通知系統")
# files = create_empty_router("檔案管理")