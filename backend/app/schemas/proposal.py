"""
提案系統 API Schemas
定義提案相關的 API 輸入輸出驗證格式
支援提案 CRUD、審核、搜尋等功能
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator, root_validator
from bson import ObjectId

from app.models.base import PyObjectId
from app.models.proposal import ProposalStatus, Industry, CompanySize


# ==================== 基礎 Schemas ====================

class ProposalBase(BaseModel):
    """提案基礎資料"""
    
    class Config:
        use_enum_values = True
        json_encoders = {ObjectId: str}


# 在 backend/app/schemas/proposal.py 中找到 CompanyInfoCreate 類別，並修改如下：

class CompanyInfoCreate(BaseModel):
    """公司資訊創建/更新"""
    company_name: str = Field(..., min_length=2, max_length=100, description="公司名稱")
    industry: Industry = Field(..., description="行業分類")
    company_size: Optional[CompanySize] = Field(None, description="公司規模")  # 添加這行
    sub_industry: Optional[str] = Field(None, max_length=50, description="細分行業")
    established_year: int = Field(..., ge=1900, le=2030, description="成立年份")
    headquarters: str = Field(..., min_length=2, max_length=50, description="總部地點")
    employee_count: int = Field(..., ge=1, le=100000, description="員工數量")
    website: Optional[str] = Field(None, pattern=r'^https?://.+', description="公司網站")
    registration_number: Optional[str] = Field(None, max_length=20, description="統一編號")
    
    @validator('established_year')
    def validate_established_year(cls, v):
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError('成立年份不能超過當前年份')
        return v
    
    @validator('company_size', always=True)
    def set_company_size(cls, v, values):
        """根據員工數量自動設定公司規模"""
        if v is not None:
            return v  # 如果已提供，直接使用
            
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
        return CompanySize.SMALL  # 預設值
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "company_name": "創新科技有限公司",
                "industry": "科技軟體",
                "company_size": "小型企業",  # 添加到示例中
                "sub_industry": "人工智慧",
                "established_year": 2018,
                "headquarters": "台北市",
                "employee_count": 25,
                "website": "https://www.innovtech.com.tw",
                "registration_number": "53912345"
            }
        }

# 在 backend/app/schemas/proposal.py 中找到 FinancialInfoCreate 類別，並修改如下：

class FinancialInfoCreate(BaseModel):
    """財務資訊創建/更新"""
    annual_revenue: int = Field(..., ge=0, le=10000000000, description="年營收 (台幣)")
    net_profit: int = Field(..., ge=-1000000000, le=1000000000, description="淨利潤 (台幣)")
    profit_margin: Optional[float] = Field(None, ge=0, le=100, description="利潤率 (%) - 可自動計算")  # 添加這行
    growth_rate: float = Field(..., ge=-100, le=1000, description="年成長率 (%)")
    debt_ratio: float = Field(..., ge=0, le=100, description="負債比率 (%)")
    cash_flow: str = Field(..., description="現金流狀況")
    asking_price: int = Field(..., ge=0, le=50000000000, description="要價 (台幣)")
    
    # 可選的歷史數據
    revenue_history: Optional[List[Dict[str, Any]]] = Field(None, description="營收歷史")
    profit_history: Optional[List[Dict[str, Any]]] = Field(None, description="獲利歷史")
    
    @validator('cash_flow')
    def validate_cash_flow(cls, v):
        allowed_values = ["正向", "持平", "略負", "負向"]
        if v not in allowed_values:
            raise ValueError(f'現金流狀況必須是以下之一: {", ".join(allowed_values)}')
        return v
    
    @validator('profit_margin', always=True)
    def calculate_profit_margin(cls, v, values):
        """如果沒有提供 profit_margin，自動計算"""
        if v is not None:
            return v  # 如果已提供，直接使用
            
        if 'annual_revenue' in values and 'net_profit' in values:
            revenue = values['annual_revenue']
            profit = values['net_profit']
            if revenue > 0:
                calculated_margin = (profit / revenue) * 100
                return round(calculated_margin, 2)
        
        return 0.0  # 預設值
    
    class Config:
        schema_extra = {
            "example": {
                "annual_revenue": 50000000,
                "net_profit": 8000000,
                "profit_margin": 16.0,  # 添加到示例中
                "growth_rate": 35.0,
                "debt_ratio": 25.0,
                "cash_flow": "正向",
                "asking_price": 200000000
            }
        }

class BusinessModelCreate(BaseModel):
    """商業模式創建/更新"""
    business_type: str = Field(..., min_length=2, max_length=50, description="商業模式類型")
    main_products: List[str] = Field(..., min_items=1, max_items=10, description="主要產品/服務")
    target_market: List[str] = Field(..., min_items=1, max_items=10, description="目標市場")
    revenue_streams: List[str] = Field(..., min_items=1, max_items=10, description="收入來源")
    competitive_advantages: List[str] = Field(..., min_items=1, max_items=10, description="競爭優勢")
    customer_base: Dict[str, Any] = Field(..., description="客戶基礎資訊")
    supply_chain: Optional[Dict[str, Any]] = Field(None, description="供應鏈資訊")
    
    @validator('main_products', 'target_market', 'revenue_streams', 'competitive_advantages')
    def validate_string_lists(cls, v):
        for item in v:
            if not isinstance(item, str) or len(item.strip()) < 2:
                raise ValueError('列表項目必須是至少2個字元的字串')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "business_type": "B2B SaaS",
                "main_products": ["AI 分析平台", "數據諮詢服務"],
                "target_market": ["中小企業", "製造業"],
                "revenue_streams": ["訂閱費用", "顧問服務"],
                "competitive_advantages": ["技術領先", "成本優勢"],
                "customer_base": {
                    "total_customers": 150,
                    "recurring_customers": 120,
                    "churn_rate": 5
                }
            }
        }


class TeaserContentCreate(BaseModel):
    """公開預覽內容創建/更新"""
    title: str = Field(..., min_length=5, max_length=100, description="提案標題")
    tagline: str = Field(..., min_length=10, max_length=200, description="一句話描述")
    summary: str = Field(..., min_length=50, max_length=500, description="簡短摘要")
    highlights: List[str] = Field(..., min_items=3, max_items=5, description="核心亮點")
    investment_opportunity: str = Field(..., min_length=20, max_length=300, description="投資機會說明")
    
    # 公開的財務範圍
    revenue_range: str = Field(..., description="營收範圍")
    growth_rate_range: str = Field(..., description="成長率範圍")
    asking_price_range: str = Field(..., description="價格範圍")
    
    @validator('highlights')
    def validate_highlights(cls, v):
        if len(v) < 3 or len(v) > 5:
            raise ValueError('亮點數量必須在 3-5 個之間')
        for highlight in v:
            if len(highlight.strip()) < 3:
                raise ValueError('每個亮點至少需要3個字元')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "title": "領先的 AI 解決方案提供商",
                "tagline": "為中小企業提供智能化轉型解決方案",
                "summary": "專注於企業 AI 轉型的科技公司，擁有多項專利技術和穩定客戶群",
                "highlights": ["AI 專利技術", "穩定客戶群", "高成長率", "優秀團隊"],
                "investment_opportunity": "隨著 AI 市場快速發展，公司具備強大的技術實力和市場地位",
                "revenue_range": "3-8千萬",
                "growth_rate_range": "25-40%",
                "asking_price_range": "1-3億"
            }
        }


class FullContentCreate(BaseModel):
    """完整內容創建/更新"""
    detailed_description: str = Field(..., min_length=100, description="詳細公司描述")
    business_plan: str = Field(..., min_length=100, description="商業計劃")
    financial_statements: Optional[str] = Field(None, description="財務報表說明")
    growth_strategy: str = Field(..., min_length=50, description="成長策略")
    risk_factors: List[str] = Field(..., min_items=1, max_items=10, description="風險因素")
    management_team: List[Dict[str, Any]] = Field(..., min_items=1, description="管理團隊")
    operational_metrics: Dict[str, Any] = Field(..., description="營運指標")
    market_analysis: str = Field(..., min_length=100, description="市場分析")
    exit_strategy: Optional[str] = Field(None, description="退出策略")
    
    detailed_financials: Dict[str, Any] = Field(..., description="詳細財務數據")
    projections: Optional[Dict[str, Any]] = Field(None, description="財務預測")
    
    @validator('risk_factors')
    def validate_risk_factors(cls, v):
        for risk in v:
            if not isinstance(risk, str) or len(risk.strip()) < 5:
                raise ValueError('風險因素必須是至少5個字元的字串')
        return v
    
    @validator('management_team')
    def validate_management_team(cls, v):
        required_fields = ['name', 'position']
        for member in v:
            for field in required_fields:
                if field not in member or not member[field]:
                    raise ValueError(f'管理團隊成員必須包含 {field} 欄位')
        return v


# ==================== 創建 Schemas ====================

class ProposalCreate(ProposalBase):
    """創建提案請求"""
    company_info: CompanyInfoCreate
    financial_info: FinancialInfoCreate
    business_model: BusinessModelCreate
    teaser_content: TeaserContentCreate
    full_content: Optional[FullContentCreate] = None
    
    class Config:
        schema_extra = {
            "example": {
                "company_info": {
                    "company_name": "創新科技有限公司",
                    "industry": "科技軟體",
                    "established_year": 2018,
                    "headquarters": "台北市",
                    "employee_count": 25
                },
                "financial_info": {
                    "annual_revenue": 50000000,
                    "net_profit": 8000000,
                    "growth_rate": 35.0,
                    "debt_ratio": 25.0,
                    "cash_flow": "正向",
                    "asking_price": 200000000
                },
                "business_model": {
                    "business_type": "B2B SaaS",
                    "main_products": ["AI 分析平台"],
                    "target_market": ["中小企業"],
                    "revenue_streams": ["訂閱費用"],
                    "competitive_advantages": ["技術領先"],
                    "customer_base": {"total_customers": 150}
                },
                "teaser_content": {
                    "title": "領先的 AI 解決方案提供商",
                    "tagline": "為中小企業提供智能化轉型解決方案",
                    "summary": "專注於企業 AI 轉型的科技公司",
                    "highlights": ["AI 專利技術", "穩定客戶群", "高成長率"],
                    "investment_opportunity": "AI 市場快速發展機會",
                    "revenue_range": "3-8千萬",
                    "growth_rate_range": "25-40%",
                    "asking_price_range": "1-3億"
                }
            }
        }


class ProposalUpdate(BaseModel):
    """更新提案請求"""
    company_info: Optional[CompanyInfoCreate] = None
    financial_info: Optional[FinancialInfoCreate] = None
    business_model: Optional[BusinessModelCreate] = None
    teaser_content: Optional[TeaserContentCreate] = None
    full_content: Optional[FullContentCreate] = None
    
    @root_validator(skip_on_failure=True)
    def validate_at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError('至少需要更新一個欄位')
        return values


# ==================== 回應 Schemas ====================

class CompanyInfoResponse(CompanyInfoCreate):
    """公司資訊回應"""
    company_size: CompanySize
    
    class Config:
        use_enum_values = True


class FinancialInfoResponse(FinancialInfoCreate):
    """財務資訊回應"""
    profit_margin: float = Field(..., description="利潤率 (自動計算)")


class AttachedFileResponse(BaseModel):
    """附件檔案回應"""
    file_id: str
    filename: str
    file_type: str
    file_size: int
    upload_time: datetime
    is_public: bool
    description: Optional[str] = None
    
    class Config:
        json_encoders = {ObjectId: str}


class ReviewRecordResponse(BaseModel):
    """審核記錄回應"""
    reviewer_id: str
    reviewer_name: str
    action: str
    comment: Optional[str] = None
    reviewed_at: datetime
    
    class Config:
        json_encoders = {ObjectId: str}


class ProposalResponse(ProposalBase):
    """提案詳細回應"""
    id: str = Field(alias="_id")
    creator_id: str
    status: ProposalStatus
    version: int
    is_active: bool
    
    company_info: CompanyInfoResponse
    financial_info: FinancialInfoResponse
    business_model: BusinessModelCreate
    teaser_content: TeaserContentCreate
    full_content: Optional[FullContentCreate] = None
    
    attached_files: List[AttachedFileResponse] = []
    review_records: List[ReviewRecordResponse] = []
    rejection_reason: Optional[str] = None
    
    view_count: int
    sent_count: int
    interest_count: int
    
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class ProposalTeaserResponse(ProposalBase):
    """提案公開預覽回應 (買方可見)"""
    id: str = Field(alias="_id")
    
    # 基本公司資訊
    industry: Industry
    company_size: CompanySize
    headquarters: str
    established_year: int
    
    # 公開預覽內容
    teaser_content: TeaserContentCreate
    
    # 統計資訊
    view_count: int
    created_at: datetime
    
    class Config:
        allow_population_by_field_name = True
        use_enum_values = True


class ProposalListResponse(BaseModel):
    """提案列表回應"""
    proposals: List[Union[ProposalResponse, ProposalTeaserResponse]]
    total: int
    page: int
    size: int
    total_pages: int
    
    class Config:
        schema_extra = {
            "example": {
                "proposals": [],
                "total": 25,
                "page": 1,
                "size": 10,
                "total_pages": 3
            }
        }


# ==================== 搜尋和篩選 Schemas ====================

class ProposalSearchParams(BaseModel):
    """提案搜尋參數"""
    # 基本搜尋
    keyword: Optional[str] = Field(None, max_length=100, description="關鍵字搜尋")
    
    # 狀態篩選
    status: Optional[List[ProposalStatus]] = Field(None, description="狀態篩選")
    
    # 行業篩選
    industries: Optional[List[Industry]] = Field(None, description="行業篩選")
    
    # 財務範圍篩選
    min_revenue: Optional[int] = Field(None, ge=0, description="最小年營收")
    max_revenue: Optional[int] = Field(None, ge=0, description="最大年營收")
    min_asking_price: Optional[int] = Field(None, ge=0, description="最小要價")
    max_asking_price: Optional[int] = Field(None, ge=0, description="最大要價")
    
    # 公司規模篩選
    company_sizes: Optional[List[CompanySize]] = Field(None, description="公司規模篩選")
    
    # 地區篩選
    regions: Optional[List[str]] = Field(None, description="地區篩選")
    
    # 時間範圍篩選
    created_after: Optional[datetime] = Field(None, description="創建時間起始")
    created_before: Optional[datetime] = Field(None, description="創建時間結束")
    
    # 排序參數
    sort_by: Optional[str] = Field("created_at", description="排序欄位")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="排序方向")
    
    # 分頁參數
    page: int = Field(1, ge=1, description="頁碼")
    size: int = Field(10, ge=1, le=100, description="每頁數量")
    
    @validator('max_revenue')
    def validate_revenue_range(cls, v, values):
        if v is not None and 'min_revenue' in values and values['min_revenue'] is not None:
            if v < values['min_revenue']:
                raise ValueError('最大年營收不能小於最小年營收')
        return v
    
    @validator('max_asking_price')
    def validate_asking_price_range(cls, v, values):
        if v is not None and 'min_asking_price' in values and values['min_asking_price'] is not None:
            if v < values['min_asking_price']:
                raise ValueError('最大要價不能小於最小要價')
        return v
    
    @validator('created_before')
    def validate_date_range(cls, v, values):
        if v is not None and 'created_after' in values and values['created_after'] is not None:
            if v < values['created_after']:
                raise ValueError('結束時間不能早於開始時間')
        return v
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "keyword": "AI 科技",
                "status": ["approved", "available"],
                "industries": ["科技軟體", "電子製造"],
                "min_revenue": 10000000,
                "max_revenue": 100000000,
                "company_sizes": ["小型企業", "中型企業"],
                "regions": ["台北市", "新竹縣市"],
                "sort_by": "created_at",
                "sort_order": "desc",
                "page": 1,
                "size": 10
            }
        }


# ==================== 審核相關 Schemas ====================

class ProposalSubmitRequest(BaseModel):
    """提交審核請求"""
    full_content: FullContentCreate
    
    class Config:
        schema_extra = {
            "example": {
                "full_content": {
                    "detailed_description": "詳細的公司描述內容...",
                    "business_plan": "完整的商業計劃...",
                    "growth_strategy": "公司未來發展策略...",
                    "risk_factors": ["市場競爭風險", "技術變化風險"],
                    "management_team": [
                        {"name": "張三", "position": "執行長", "experience": "10年"}
                    ],
                    "operational_metrics": {"customer_satisfaction": 95},
                    "market_analysis": "市場分析內容...",
                    "detailed_financials": {"monthly_recurring_revenue": 1000000}
                }
            }
        }


class ProposalApproveRequest(BaseModel):
    """核准提案請求"""
    comment: Optional[str] = Field(None, max_length=500, description="審核意見")
    
    class Config:
        schema_extra = {
            "example": {
                "comment": "提案內容完整，財務數據合理，核准發布"
            }
        }


class ProposalRejectRequest(BaseModel):
    """拒絕提案請求"""
    reason: str = Field(..., min_length=10, max_length=500, description="拒絕原因")
    
    class Config:
        schema_extra = {
            "example": {
                "reason": "財務數據需要更詳細的說明，請補充過去三年的詳細財報"
            }
        }


# ==================== 統計相關 Schemas ====================

class ProposalStatsResponse(BaseModel):
    """提案統計回應"""
    total_proposals: int
    draft_count: int
    under_review_count: int
    approved_count: int
    rejected_count: int
    available_count: int
    sent_count: int
    archived_count: int
    
    total_views: int
    total_sent: int
    total_interest: int
    
    industry_distribution: Dict[str, int]
    monthly_creation_trend: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "total_proposals": 25,
                "draft_count": 5,
                "under_review_count": 3,
                "approved_count": 10,
                "rejected_count": 2,
                "available_count": 8,
                "sent_count": 5,
                "archived_count": 0,
                "total_views": 250,
                "total_sent": 15,
                "total_interest": 8,
                "industry_distribution": {
                    "科技軟體": 10,
                    "製造業": 8,
                    "服務業": 7
                },
                "monthly_creation_trend": [
                    {"month": "2025-01", "count": 5},
                    {"month": "2025-02", "count": 8}
                ]
            }
        }


# ==================== 通用回應 Schemas ====================

class SuccessResponse(BaseModel):
    """成功回應"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "操作成功",
                "data": None
            }
        }


class ErrorResponse(BaseModel):
    """錯誤回應"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "請求參數錯誤",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "company_name", "issue": "欄位不能為空"}
            }
        }