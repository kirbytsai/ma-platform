"""
基礎資料模型類別
"""
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict


class PyObjectId(ObjectId):
    """自定義 ObjectId 類別，用於 Pydantic 模型"""
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        """Pydantic v2 兼容方法"""
        from pydantic_core import core_schema
        return core_schema.str_schema()
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class TimestampMixin:
    """時間戳記混入類別"""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def update_timestamp(self):
        """更新時間戳記"""
        self.updated_at = datetime.utcnow()


class SoftDeleteMixin:
    """軟刪除混入類別"""
    
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)
    
    def soft_delete(self):
        """執行軟刪除"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """恢復軟刪除"""
        self.is_deleted = False
        self.deleted_at = None


class BaseDocument(BaseModel):
    """基礎文檔模型"""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)
    
    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """轉換為字典"""
        data = self.model_dump(by_alias=True, exclude_none=exclude_none)
        
        # 處理 ObjectId
        if "_id" in data and data["_id"]:
            data["_id"] = str(data["_id"])
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """從字典建立實例"""
        return cls(**data)
    
    def update_timestamp(self):
        """更新時間戳記"""
        self.updated_at = datetime.utcnow()
    
    def soft_delete(self):
        """執行軟刪除"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.update_timestamp()
    
    def restore(self):
        """恢復軟刪除"""
        self.is_deleted = False
        self.deleted_at = None
        self.update_timestamp()


class AuditMixin:
    """審計混入類別"""
    
    created_by: Optional[str] = Field(default=None)
    updated_by: Optional[str] = Field(default=None)
    
    def set_created_by(self, user_id: str):
        """設定建立者"""
        self.created_by = user_id
    
    def set_updated_by(self, user_id: str):
        """設定更新者"""
        self.updated_by = user_id


# 通用響應模型
class BaseResponse(BaseModel):
    """基礎響應模型"""
    
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseResponse):
    """分頁響應模型"""
    
    data: Optional[list] = None
    pagination: Optional[Dict[str, Any]] = None
    
    @classmethod
    def create(
        cls,
        items: list,
        total: int,
        page: int,
        page_size: int,
        message: Optional[str] = None
    ):
        """建立分頁響應"""
        total_pages = (total + page_size - 1) // page_size
        
        return cls(
            success=True,
            message=message,
            data=items,
            pagination={
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        )


class ErrorResponse(BaseResponse):
    """錯誤響應模型"""
    
    success: bool = False
    data: Optional[Any] = None
    
    @classmethod
    def create(
        cls,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """建立錯誤響應"""
        return cls(
            success=False,
            message=message,
            error={
                "code": error_code,
                "details": details
            }
        )