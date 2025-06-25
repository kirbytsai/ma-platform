"""
認證 API 端點
處理用戶註冊、登入、Token 管理等認證相關的 HTTP 請求
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, RefreshTokenRequest,
    AccessTokenResponse, PasswordChange, UserRegisterResponse,
    UserLoginResponse, LogoutResponse, PasswordChangeResponse,
    AuthResponses
)
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service
from app.models.user import User, UserRole
from app.api.deps import get_current_active_user
from app.core.exceptions import BusinessException, ValidationException, PermissionDeniedException


# 建立認證路由器
router = APIRouter(prefix="/auth", tags=["認證"])


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses=AuthResponses.REGISTER_SUCCESS | AuthResponses.AUTH_ERRORS,
    summary="用戶註冊",
    description="註冊新用戶帳號 (買方或提案方，不包含管理員)"
)
async def register_user(user_data: UserRegister):
    """
    用戶註冊端點
    
    - **email**: 用戶電子郵件 (必須唯一)
    - **password**: 用戶密碼 (最少8字元)
    - **role**: 用戶角色 (buyer 或 seller)
    - **first_name**: 名字
    - **last_name**: 姓氏
    - **phone**: 電話號碼 (可選)
    - **buyer_profile**: 買方初始資料 (可選)
    - **seller_profile**: 提案方初始資料 (可選)
    
    返回用戶資料和認證 Token
    """
    try:
        # 準備角色專屬資料
        profile_data = None
        if user_data.role == UserRole.BUYER and user_data.buyer_profile:
            profile_data = user_data.buyer_profile
        elif user_data.role == UserRole.SELLER and user_data.seller_profile:
            profile_data = user_data.seller_profile
        
        # 註冊用戶
        user, tokens = await auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            role=user_data.role,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            profile_data=profile_data
        )
        
        # 準備回應資料
        user_dict = user.to_dict(include_sensitive=False)
        
        return UserRegisterResponse(
            success=True,
            message="註冊成功",
            user=user_dict,
            tokens=TokenResponse(**tokens)
        )
        
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "message": e.message,
                "error_code": e.error_code
            }
        )
    except BusinessException as e:
        if e.error_code == "USER_EMAIL_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
    except PermissionDeniedException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": e.message,
                "error_code": e.error_code
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "註冊過程發生錯誤",
                "error_code": "REGISTRATION_INTERNAL_ERROR"
            }
        )


@router.post(
    "/login",
    response_model=UserLoginResponse,
    responses=AuthResponses.LOGIN_SUCCESS | AuthResponses.AUTH_ERRORS,
    summary="用戶登入",
    description="用戶登入並取得認證 Token"
)
async def login_user(login_data: UserLogin):
    """
    用戶登入端點
    
    - **email**: 用戶電子郵件
    - **password**: 用戶密碼  
    - **remember_me**: 記住我 (延長 Token 有效期)
    
    返回用戶資料和認證 Token
    """
    try:
        # 用戶登入
        user, tokens = await auth_service.authenticate_user(
            email=login_data.email,
            password=login_data.password,
            remember_me=login_data.remember_me
        )
        
        # 準備回應資料
        user_dict = user.to_dict(include_sensitive=False)
        
        return UserLoginResponse(
            success=True,
            message="登入成功",
            user=user_dict,
            tokens=TokenResponse(**tokens)
        )
        
    except BusinessException as e:
        if e.error_code in ["INVALID_CREDENTIALS"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
        elif e.error_code == "ACCOUNT_DISABLED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "登入過程發生錯誤",
                "error_code": "LOGIN_INTERNAL_ERROR"
            }
        )


@router.get(
    "/me",
    response_model=UserResponse,
    responses=AuthResponses.AUTH_ERRORS,
    summary="取得當前用戶資料",
    description="取得當前認證用戶的完整資料"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    取得當前用戶資料端點
    
    需要提供有效的 Access Token
    
    返回當前用戶的完整資料 (不包含敏感資訊)
    """
    try:
        # 修復：正確處理用戶資料轉換
        user_dict = current_user.to_dict(include_sensitive=False)
        
        # 確保 ObjectId 正確轉換為字串
        if "_id" in user_dict:
            user_dict["id"] = str(user_dict["_id"])
            del user_dict["_id"]
        
        # 如果沒有 id 欄位，使用 current_user.id
        if "id" not in user_dict and hasattr(current_user, 'id'):
            user_dict["id"] = current_user.id
        
        return user_dict  # 直接返回字典，讓 FastAPI 自動轉換
        
    except Exception as e:
        # 添加更詳細的錯誤日誌
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Get user info error: {str(e)}, user_data: {current_user}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"取得用戶資料失敗: {str(e)}",
                "error_code": "GET_USER_INFO_ERROR"
            }
        )

@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    responses=AuthResponses.TOKEN_REFRESH_SUCCESS | AuthResponses.AUTH_ERRORS,
    summary="刷新 Access Token",
    description="使用 Refresh Token 刷新 Access Token"
)
async def refresh_access_token(token_data: RefreshTokenRequest):
    """
    刷新 Access Token 端點
    
    - **refresh_token**: 有效的 Refresh Token
    
    返回新的 Access Token
    """
    try:
        # 刷新 Token
        new_token_data = await auth_service.refresh_access_token(
            refresh_token=token_data.refresh_token
        )
        
        return AccessTokenResponse(**new_token_data)
        
    except BusinessException as e:
        if e.error_code in ["INVALID_REFRESH_TOKEN", "INVALID_TOKEN_TYPE"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
        elif e.error_code in ["USER_NOT_FOUND", "ACCOUNT_DISABLED"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Token 刷新失敗",
                "error_code": "TOKEN_REFRESH_INTERNAL_ERROR"
            }
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses=AuthResponses.LOGOUT_SUCCESS | AuthResponses.AUTH_ERRORS,
    summary="用戶登出",
    description="用戶登出並失效 Refresh Token"
)
async def logout_user(
    token_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    用戶登出端點
    
    - **refresh_token**: 要失效的 Refresh Token
    
    需要提供有效的 Access Token 進行身份驗證
    """
    try:
        # 登出用戶 (將 Refresh Token 加入黑名單)
        success = await auth_service.logout_user(
            refresh_token=token_data.refresh_token
        )
        
        if success:
            return LogoutResponse(
                success=True,
                message="登出成功"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "登出失敗",
                    "error_code": "LOGOUT_FAILED"
                }
            )
            
    except Exception as e:
        # 即使登出過程出錯，也返回成功 (安全考量)
        return LogoutResponse(
            success=True,
            message="登出成功"
        )


@router.put(
    "/change-password",
    response_model=PasswordChangeResponse,
    responses=AuthResponses.PASSWORD_CHANGE_SUCCESS | AuthResponses.AUTH_ERRORS,
    summary="修改密碼",
    description="修改當前用戶的密碼"
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user)
):
    """
    修改密碼端點
    
    - **current_password**: 目前密碼
    - **new_password**: 新密碼 (最少8字元)
    - **confirm_new_password**: 確認新密碼
    
    需要提供有效的 Access Token 進行身份驗證
    """
    try:
        # 修改密碼
        success = await auth_service.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        if success:
            return PasswordChangeResponse(
                success=True,
                message="密碼修改成功"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "密碼修改失敗",
                    "error_code": "PASSWORD_CHANGE_FAILED"
                }
            )
            
    except BusinessException as e:
        if e.error_code == "INVALID_OLD_PASSWORD":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": e.message,
                    "error_code": e.error_code
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "密碼修改過程發生錯誤",
                "error_code": "PASSWORD_CHANGE_INTERNAL_ERROR"
            }
        )


# 開發和測試用端點 (生產環境應移除)
@router.get(
    "/test",
    summary="認證測試端點",
    description="測試認證系統是否正常運作 (開發用)"
)
async def test_auth():
    """
    認證測試端點
    
    用於測試認證系統的基本功能
    生產環境中應該移除此端點
    """
    return {
        "success": True,
        "message": "認證系統正常運作",
        "timestamp": "2023-12-01T10:00:00Z",
        "version": "1.0.0"
    }


@router.get(
    "/protected-test",
    summary="受保護端點測試",
    description="測試需要認證的端點 (開發用)"
)
async def test_protected_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    """
    受保護端點測試
    
    需要提供有效的 Access Token
    用於測試認證中介軟體是否正常運作
    """
    return {
        "success": True,
        "message": "認證成功",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "user_role": current_user.role,
        "timestamp": "2023-12-01T10:00:00Z"
    }