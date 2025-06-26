"""
提案系統資料模型
包含提案的完整生命週期管理、內容結構和狀態流轉
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
from bson import ObjectId

from app.models.base import PyObjectId, TimestampMixin


class ProposalStatus(str, Enum):
    """提案狀態枚舉"""
    DRAFT = "draft"                    # 草稿
    UNDER_REVIEW = "under_review"      # 審核中
    APPROVED = "approved"              # 已核准
    REJECTED = "rejected"              # 已拒絕
    AVAILABLE = "available"            # 可發送 (已核准且發布)
    SENT = "sent"                      # 已發送給買方
    ARCHIVED = "archived"              # 已封存


class Industry(str, Enum):
    """行業分類枚舉"""
    TECHNOLOGY = "科技軟體"
    ELECTRONICS = "電子製造"
    BIOTECHNOLOGY = "生物科技"
    FINANCE = "金融服務"
    RETAIL = "零售電商"
    FOOD_SERVICE = "餐飲服務"
    MANUFACTURING = "製造業"
    REAL_ESTATE = "房地產"
    HEALTHCARE = "醫療健康"
    EDUCATION = "教育培訓"
    LOGISTICS = "物流運輸"
    ENERGY = "能源環保"
    MEDIA = "文創媒體"
    AGRICULTURE = "農業食品"
    TOURISM = "旅遊觀光"
    OTHER = "其他"


class CompanySize(str, Enum):
    """公司規模枚舉"""
    MICRO = "微型企業"      # 1-4人
    SMALL = "小型企業"      # 5-29人
    MEDIUM = "中型企業"     # 30-199人
    LARGE = "大型企業"      # 200-999人
    ENTERPRISE = "超大型企業"  # 1000人以上


class CompanyInfo(BaseModel):
    """公司基本資訊"""
    company_name: str = Field(..., description="公司名稱")
    industry: Industry = Field(..., description="行業分類")
    sub_industry: Optional[str] = Field(None, description="細分行業")
    established_year: int = Field(..., ge=1900, le=2030, description="成立年份")
    headquarters: str = Field(..., description="總部地點")
    employee_count: int = Field(..., ge=1, description="員工數量")
    company_size: CompanySize = Field(..., description="公司規模")
    website: Optional[str] = Field(None, description="公司網站")
    registration_number: Optional[str] = Field(None, description="統一編號")
    
    @validator('established_year')
    def validate_established_year(cls, v):
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError('成立年份不能超過當前年份')
        return v
    
    @validator('company_size', always=True)
    def set_company_size(cls, v, values):
        """根據員工數量自動設定公司規模"""
        if 'employee_count' in values:
            count = values['employee_count']
            if count <= 4:
                return CompanySize.MICRO
            elif count <= 29:
                return CompanySize.SMALL
            elif count <= 199:
                return CompanySize.MEDIUM
            elif count <= 999:
                return CompanySize.LARGE
            else:
                return CompanySize.ENTERPRISE
        return v


class FinancialInfo(BaseModel):
    """財務資訊"""
    annual_revenue: int = Field(..., ge=0, description="年營收 (台幣)")
    net_profit: int = Field(..., description="淨利潤 (台幣)")
    profit_margin: float = Field(..., ge=0, le=100, description="利潤率 (%)")
    growth_rate: float = Field(..., ge=-100, le=1000, description="年成長率 (%)")
    debt_ratio: float = Field(..., ge=0, le=100, description="負債比率 (%)")
    cash_flow: str = Field(..., description="現金流狀況")
    asking_price: int = Field(..., ge=0, description="要價 (台幣)")
    
    # 財務歷史數據 (可選)
    revenue_history: Optional[List[Dict[str, Any]]] = Field(None, description="營收歷史")
    profit_history: Optional[List[Dict[str, Any]]] = Field(None, description="獲利歷史")
    
    @validator('profit_margin', always=True)
    def calculate_profit_margin(cls, v, values):
        """自動計算利潤率"""
        if 'annual_revenue' in values and 'net_profit' in values:
            revenue = values['annual_revenue']
            profit = values['net_profit']
            if revenue > 0:
                calculated_margin = (profit / revenue) * 100
                return round(calculated_margin, 2)
        return v


class BusinessModel(BaseModel):
    """商業模式資訊"""
    business_type: str = Field(..., description="商業模式類型")
    main_products: List[str] = Field(..., description="主要產品/服務")
    target_market: List[str] = Field(..., description="目標市場")
    revenue_streams: List[str] = Field(..., description="收入來源")
    competitive_advantages: List[str] = Field(..., description="競爭優勢")
    customer_base: Dict[str, Any] = Field(..., description="客戶基礎資訊")
    supply_chain: Optional[Dict[str, Any]] = Field(None, description="供應鏈資訊")


class TeaserContent(BaseModel):
    """公開預覽內容 (買方可見)"""
    title: str = Field(..., max_length=100, description="提案標題")
    tagline: str = Field(..., max_length=200, description="一句話描述")
    summary: str = Field(..., max_length=500, description="簡短摘要")
    highlights: List[str] = Field(..., description="核心亮點 (3-5個)")
    investment_opportunity: str = Field(..., max_length=300, description="投資機會說明")
    
    # 公開的基本財務資訊
    revenue_range: str = Field(..., description="營收範圍 (如: 1-5千萬)")
    growth_rate_range: str = Field(..., description="成長率範圍")
    asking_price_range: str = Field(..., description="價格範圍")
    
    @validator('highlights')
    def validate_highlights(cls, v):
        if len(v) < 3 or len(v) > 5:
            raise ValueError('亮點數量應該在 3-5 個之間')
        return v


class FullContent(BaseModel):
    """完整內容 (NDA 後可見)"""
    detailed_description: str = Field(..., description="詳細公司描述")
    business_plan: str = Field(..., description="商業計劃")
    financial_statements: Optional[str] = Field(None, description="財務報表說明")
    growth_strategy: str = Field(..., description="成長策略")
    risk_factors: List[str] = Field(..., description="風險因素")
    management_team: List[Dict[str, Any]] = Field(..., description="管理團隊")
    operational_metrics: Dict[str, Any] = Field(..., description="營運指標")
    market_analysis: str = Field(..., description="市場分析")
    exit_strategy: Optional[str] = Field(None, description="退出策略")
    
    # 詳細財務數據
    detailed_financials: Dict[str, Any] = Field(..., description="詳細財務數據")
    projections: Optional[Dict[str, Any]] = Field(None, description="財務預測")


class AttachedFile(BaseModel):
    """附件檔案"""
    file_id: PyObjectId = Field(default_factory=PyObjectId, description="檔案ID")
    filename: str = Field(..., description="檔案名稱")
    file_type: str = Field(..., description="檔案類型")
    file_size: int = Field(..., ge=0, description="檔案大小 (bytes)")
    upload_time: datetime = Field(default_factory=datetime.utcnow, description="上傳時間")
    file_path: str = Field(..., description="檔案路徑")
    is_public: bool = Field(False, description="是否為公開檔案")
    description: Optional[str] = Field(None, description="檔案描述")


class ReviewRecord(BaseModel):
    """審核記錄"""
    reviewer_id: PyObjectId = Field(..., description="審核者ID")
    reviewer_name: str = Field(..., description="審核者姓名")
    action: str = Field(..., description="審核動作")  # approve, reject, request_changes
    comment: Optional[str] = Field(None, description="審核意見")
    reviewed_at: datetime = Field(default_factory=datetime.utcnow, description="審核時間")
    
    class Config:
        json_encoders = {ObjectId: str}


class Proposal(TimestampMixin):
    """提案主模型"""
    
    # 基本資訊
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    creator_id: PyObjectId = Field(..., description="創建者ID (提案方)")
    
    # 狀態管理
    status: ProposalStatus = Field(default=ProposalStatus.DRAFT, description="提案狀態")
    version: int = Field(default=1, description="版本號")
    is_active: bool = Field(default=True, description="是否啟用")
    
    # 公司與商業資訊
    company_info: CompanyInfo = Field(..., description="公司基本資訊")
    financial_info: FinancialInfo = Field(..., description="財務資訊")
    business_model: BusinessModel = Field(..., description="商業模式")
    
    # 內容結構
    teaser_content: TeaserContent = Field(..., description="公開預覽內容")
    full_content: Optional[FullContent] = Field(None, description="完整內容")
    
    # 檔案管理
    attached_files: List[AttachedFile] = Field(default_factory=list, description="附件檔案")
    
    # 審核相關
    review_records: List[ReviewRecord] = Field(default_factory=list, description="審核記錄")
    rejection_reason: Optional[str] = Field(None, description="拒絕原因")
    
    # 統計資訊
    view_count: int = Field(default=0, description="瀏覽次數")
    sent_count: int = Field(default=0, description="發送次數")
    interest_count: int = Field(default=0, description="表達興趣次數")
    
    # 時間戳記
    submitted_at: Optional[datetime] = Field(None, description="提交審核時間")
    approved_at: Optional[datetime] = Field(None, description="核准時間")
    published_at: Optional[datetime] = Field(None, description="發布時間")
    
    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "company_info": {
                    "company_name": "創新科技有限公司",
                    "industry": "科技軟體",
                    "established_year": 2018,
                    "headquarters": "台北市",
                    "employee_count": 25,
                    "website": "https://www.innovtech.com.tw"
                },
                "financial_info": {
                    "annual_revenue": 50000000,
                    "net_profit": 8000000,
                    "profit_margin": 16.0,
                    "growth_rate": 35.0,
                    "asking_price": 200000000
                },
                "teaser_content": {
                    "title": "領先的 AI 解決方案提供商",
                    "summary": "專注於企業 AI 轉型的科技公司，擁有多項專利技術",
                    "highlights": ["AI 專利技術", "穩定客戶群", "高成長率", "優秀團隊"]
                }
            }
        }
    
    @validator('status')
    def validate_status_transition(cls, v, values):
        """驗證狀態轉換的合法性"""
        # 這裡可以添加狀態轉換邏輯驗證
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_content_completeness(cls, values):
        """根據狀態驗證內容完整性"""
        status = values.get('status')
        
        if status in [ProposalStatus.UNDER_REVIEW, ProposalStatus.APPROVED, ProposalStatus.AVAILABLE]:
            # 提交審核時必須有完整內容
            if not values.get('full_content'):
                raise ValueError('提交審核時必須提供完整內容')
        
        return values
    
    # 業務方法
    def can_edit(self) -> bool:
        """檢查是否可以編輯"""
        return self.status in [ProposalStatus.DRAFT, ProposalStatus.REJECTED]
    
    def can_submit(self) -> bool:
        """檢查是否可以提交審核"""
        return self.status == ProposalStatus.DRAFT and self.full_content is not None
    
    def can_approve(self) -> bool:
        """檢查是否可以核准"""
        return self.status == ProposalStatus.UNDER_REVIEW
    
    def can_send(self) -> bool:
        """檢查是否可以發送"""
        return self.status in [ProposalStatus.APPROVED, ProposalStatus.AVAILABLE]
    
    def submit_for_review(self) -> None:
        """提交審核"""
        if not self.can_submit():
            raise ValueError("當前狀態不允許提交審核")
        
        self.status = ProposalStatus.UNDER_REVIEW
        self.submitted_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def approve(self, reviewer_id: str, reviewer_name: str, comment: Optional[str] = None) -> None:
        """核准提案"""
        if not self.can_approve():
            raise ValueError("當前狀態不允許核准")
        
        self.status = ProposalStatus.APPROVED
        self.approved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # 記錄審核
        review_record = ReviewRecord(
            reviewer_id=PyObjectId(reviewer_id),
            reviewer_name=reviewer_name,
            action="approve",
            comment=comment
        )
        self.review_records.append(review_record)
    
    def reject(self, reviewer_id: str, reviewer_name: str, reason: str) -> None:
        """拒絕提案"""
        if not self.can_approve():
            raise ValueError("當前狀態不允許拒絕")
        
        self.status = ProposalStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()
        
        # 記錄審核
        review_record = ReviewRecord(
            reviewer_id=PyObjectId(reviewer_id),
            reviewer_name=reviewer_name,
            action="reject",
            comment=reason
        )
        self.review_records.append(review_record)
    
    def publish(self) -> None:
        """發布提案 (核准後可發送)"""
        if self.status != ProposalStatus.APPROVED:
            raise ValueError("只有已核准的提案才能發布")
        
        self.status = ProposalStatus.AVAILABLE
        self.published_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def increment_view(self) -> None:
        """增加瀏覽次數"""
        self.view_count += 1
        self.updated_at = datetime.utcnow()
    
    def increment_sent(self) -> None:
        """增加發送次數"""
        self.sent_count += 1
        if self.status == ProposalStatus.AVAILABLE:
            self.status = ProposalStatus.SENT
        self.updated_at = datetime.utcnow()
    
    def increment_interest(self) -> None:
        """增加興趣次數"""
        self.interest_count += 1
        self.updated_at = datetime.utcnow()
    
    def get_public_info(self) -> Dict[str, Any]:
        """取得公開資訊 (買方可見)"""
        return {
            "id": str(self.id),
            "company_info": {
                "industry": self.company_info.industry,
                "company_size": self.company_info.company_size,
                "headquarters": self.company_info.headquarters,
                "established_year": self.company_info.established_year
            },
            "teaser_content": self.teaser_content.dict(),
            "view_count": self.view_count,
            "created_at": self.created_at
        }
    
    def get_full_info(self) -> Dict[str, Any]:
        """取得完整資訊 (NDA 後可見)"""
        return {
            **self.get_public_info(),
            "company_info": self.company_info.dict(),
            "financial_info": self.financial_info.dict(),
            "business_model": self.business_model.dict(),
            "full_content": self.full_content.dict() if self.full_content else None,
            "attached_files": [f.dict() for f in self.attached_files if not f.is_public]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "_id": self.id,
            "creator_id": self.creator_id,
            "status": self.status,
            "version": self.version,
            "is_active": self.is_active,
            "company_info": self.company_info.dict(),
            "financial_info": self.financial_info.dict(),
            "business_model": self.business_model.dict(),
            "teaser_content": self.teaser_content.dict(),
            "full_content": self.full_content.dict() if self.full_content else None,
            "attached_files": [f.dict() for f in self.attached_files],
            "review_records": [r.dict() for r in self.review_records],
            "rejection_reason": self.rejection_reason,
            "view_count": self.view_count,
            "sent_count": self.sent_count,
            "interest_count": self.interest_count,
            "submitted_at": self.submitted_at,
            "approved_at": self.approved_at,
            "published_at": self.published_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }