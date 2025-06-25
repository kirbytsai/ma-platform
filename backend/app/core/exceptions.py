 
"""
自定義異常類別
"""
from typing import Optional, Any, Dict


class BusinessException(Exception):
    """業務邏輯異常基類"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ValidationException(BusinessException):
    """資料驗證異常"""
    
    def __init__(self, message: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(message, error_code, 422, details)


class PermissionDeniedException(BusinessException):
    """權限不足異常"""
    
    def __init__(self, message: str = "權限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "PERMISSION_DENIED", 403, details)


class ResourceNotFoundException(BusinessException):
    """資源不存在異常"""
    
    def __init__(self, resource_type: str, resource_id: str = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type}不存在"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        error_code = f"{resource_type.upper()}_NOT_FOUND"
        super().__init__(message, error_code, 404, details)


class DuplicateResourceException(BusinessException):
    """資源重複異常"""
    
    def __init__(self, resource_type: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type}已存在"
        if field:
            message += f" ({field})"
        
        error_code = f"{resource_type.upper()}_DUPLICATE"
        super().__init__(message, error_code, 409, details)


class InvalidOperationException(BusinessException):
    """無效操作異常"""
    
    def __init__(self, operation: str, reason: str = None, details: Optional[Dict[str, Any]] = None):
        message = f"無法執行操作: {operation}"
        if reason:
            message += f" ({reason})"
        
        super().__init__(message, "INVALID_OPERATION", 400, details)


# 用戶相關異常
class UserAlreadyExistsException(DuplicateResourceException):
    """用戶已存在異常"""
    
    def __init__(self, email: str):
        super().__init__("用戶", f"email: {email}")


class InvalidCredentialsException(BusinessException):
    """登入憑證無效異常"""
    
    def __init__(self):
        super().__init__("帳號或密碼錯誤", "INVALID_CREDENTIALS", 401)


class AccountDisabledException(BusinessException):
    """帳號已停用異常"""
    
    def __init__(self):
        super().__init__("帳號已被停用", "ACCOUNT_DISABLED", 401)


# 提案相關異常
class ProposalNotFoundException(ResourceNotFoundException):
    """提案不存在異常"""
    
    def __init__(self, proposal_id: str):
        super().__init__("提案", proposal_id)


class InvalidProposalStatusException(InvalidOperationException):
    """提案狀態無效異常"""
    
    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            f"提案狀態轉換", 
            f"無法從 {current_status} 轉換到 {target_status}"
        )


class ProposalLimitExceededException(BusinessException):
    """提案數量超過限制異常"""
    
    def __init__(self, limit: int):
        super().__init__(
            f"提案數量已達上限 ({limit})", 
            "PROPOSAL_LIMIT_EXCEEDED", 
            400
        )


# 案例相關異常
class CaseNotFoundException(ResourceNotFoundException):
    """案例不存在異常"""
    
    def __init__(self, case_id: str):
        super().__init__("案例", case_id)


class CaseAccessDeniedException(PermissionDeniedException):
    """案例存取權限不足異常"""
    
    def __init__(self):
        super().__init__("您沒有權限存取此案例")


class InvalidCaseStatusException(InvalidOperationException):
    """案例狀態無效異常"""
    
    def __init__(self, current_status: str, operation: str):
        super().__init__(
            operation,
            f"案例狀態 {current_status} 不允許此操作"
        )


# 檔案相關異常
class FileNotFoundException(ResourceNotFoundException):
    """檔案不存在異常"""
    
    def __init__(self, file_id: str):
        super().__init__("檔案", file_id)


class InvalidFileTypeException(ValidationException):
    """檔案類型無效異常"""
    
    def __init__(self, file_type: str, allowed_types: list):
        super().__init__(
            f"檔案類型 {file_type} 不被允許，允許的類型: {', '.join(allowed_types)}",
            "file_type"
        )


class FileSizeExceededException(ValidationException):
    """檔案大小超過限制異常"""
    
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            f"檔案大小 {file_size} bytes 超過限制 {max_size} bytes",
            "file_size"
        )


# 通知相關異常
class NotificationNotFoundException(ResourceNotFoundException):
    """通知不存在異常"""
    
    def __init__(self, notification_id: str):
        super().__init__("通知", notification_id)