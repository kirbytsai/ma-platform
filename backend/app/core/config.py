"""
應用程式配置管理
"""
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator
import secrets


class Settings(BaseSettings):
    """應用程式設定類別"""
    
    # 基本應用設定
    APP_NAME: str = "M&A Platform API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, testing, production
    
    # 伺服器設定
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 資料庫設定 - 支援 MONGODB_URL 和 MONGODB_URI 兩種名稱
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_URI: Optional[str] = None  # 兼容性支援
    MONGODB_DB_NAME: str = "ma_platform"
    MONGODB_TEST_DB_NAME: str = "ma_platform_test"
    
    # JWT 設定
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_REFRESH_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS 設定 - 使用 Union 類型來支援字串和列表
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://127.0.0.1:3000,https://localhost:3000"
    
    # Email 設定
    EMAIL_ENABLED: bool = True
    EMAIL_PROVIDER: str = "smtp"  # smtp, sendgrid
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: str = "noreply@ma-platform.com"
    FROM_NAME: str = "M&A Platform"
    
    # 檔案上傳設定
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: Union[str, List[str]] = "pdf,doc,docx,xls,xlsx,jpg,jpeg,png,gif"
    
    # 分頁設定
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # 安全設定
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_ATTEMPT_TIMEOUT_MINUTES: int = 30
    
    # API 限流設定
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # 秒
    
    # 通知設定
    NOTIFICATION_BATCH_SIZE: int = 50
    EMAIL_TEMPLATE_DIR: str = "./templates/email"
    
    # 提案系統設定
    PROPOSAL_DRAFT_AUTO_SAVE_MINUTES: int = 5
    PROPOSAL_REVIEW_TIMEOUT_DAYS: int = 7
    
    # 案例系統設定
    CASE_AUTO_ARCHIVE_DAYS: int = 30
    MESSAGE_MAX_LENGTH: int = 2000
    
    @field_validator('MONGODB_URL', mode='before')
    @classmethod
    def assemble_mongodb_url(cls, v, values=None):
        """處理 MongoDB URL 設定，支援 MONGODB_URI 和 MONGODB_URL"""
        # 如果有設定 MONGODB_URI，優先使用它
        if hasattr(values, 'data') and values.data.get('MONGODB_URI'):
            return values.data.get('MONGODB_URI')
        return v
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def assemble_cors_origins(cls, v):
        """處理 CORS 來源設定"""
        if isinstance(v, str) and v:
            # 移除空白字符並分割
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        elif v is None or v == "":
            # 如果為空，返回預設值
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000", 
                "https://localhost:3000"
            ]
        return v
    
    @field_validator('ALLOWED_FILE_TYPES', mode='before')
    @classmethod
    def assemble_file_types(cls, v):
        """處理允許的檔案類型"""
        if isinstance(v, str) and v:
            return [i.strip().lower() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [t.lower() for t in v]
        return v
    
    @property
    def database_url(self) -> str:
        """取得資料庫連接 URL"""
        if self.ENVIRONMENT == "testing":
            return f"{self.MONGODB_URL}/{self.MONGODB_TEST_DB_NAME}"
        return f"{self.MONGODB_URL}/{self.MONGODB_DB_NAME}"
    
    @property
    def is_development(self) -> bool:
        """是否為開發環境"""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_testing(self) -> bool:
        """是否為測試環境"""
        return self.ENVIRONMENT == "testing"
    
    @property
    def is_production(self) -> bool:
        """是否為生產環境"""
        return self.ENVIRONMENT == "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 建立全域設定實例
settings = Settings()


# 環境變數驗證
def validate_settings():
    """驗證必要的環境變數"""
    required_settings = []
    
    if settings.is_production:
        required_settings.extend([
            ('MONGODB_URL', settings.MONGODB_URL),
            ('JWT_SECRET', settings.JWT_SECRET),
        ])
        
        if settings.EMAIL_ENABLED:
            required_settings.extend([
                ('SMTP_USER', settings.SMTP_USER),
                ('SMTP_PASSWORD', settings.SMTP_PASSWORD),
            ])
    
    missing = [name for name, value in required_settings if not value]
    
    if missing:
        raise ValueError(f"缺少必要的環境變數: {', '.join(missing)}")
    
    print(f"✅ 環境變數驗證通過 ({settings.ENVIRONMENT})")


# 在導入時驗證設定
if settings.is_production:
    validate_settings()