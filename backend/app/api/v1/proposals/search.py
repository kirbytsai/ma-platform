"""
提案搜尋引擎 API 模組 - search.py
負責提案搜尋和篩選功能的 API 端點
對應服務: ProposalSearchService
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.proposal import Industry, CompanySize, ProposalStatus
from app.schemas.proposal import ProposalSearchParams
from app.services.proposal import ProposalService
from app.api.deps import get_current_user_optional

# 創建子路由器
router = APIRouter()

# 創建服務實例
proposal_service = ProposalService()


@router.get("/search/", response_model=Dict[str, Any])
async def search_proposals(
    q: Optional[str] = Query(None, description="搜尋關鍵字"),
    industry: Optional[Industry] = Query(None, description="產業篩選"),
    company_size: Optional[CompanySize] = Query(None, description="公司規模篩選"),
    status: Optional[ProposalStatus] = Query(None, description="狀態篩選"),
    location: Optional[str] = Query(None, description="地區篩選"),
    min_revenue: Optional[int] = Query(None, description="最小營收 (萬元)"),
    max_revenue: Optional[int] = Query(None, description="最大營收 (萬元)"),
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=100, description="每頁數量"),
    sort_by: Optional[str] = Query("updated_at", description="排序欄位"),
    sort_order: Optional[str] = Query("desc", description="排序方向 (asc/desc)"),
    current_user = Depends(get_current_user_optional)
):
    """
    智能搜尋提案
    
    - **權限**: 公開搜尋，登入用戶可看更多內容
    - **功能**: 支援關鍵字搜尋和多維度篩選
    - **服務模組**: ProposalSearchService.search_proposals()
    """
    try:
        search_params = ProposalSearchParams(
            query=q,
            industry=industry,
            company_size=company_size,
            status=status,
            location=location,
            min_revenue=min_revenue,
            max_revenue=max_revenue,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.search_proposals(search_params, user_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "search_params": {
                    "query": q,
                    "filters": {
                        "industry": industry,
                        "company_size": company_size,
                        "status": status,
                        "location": location,
                        "revenue_range": f"{min_revenue}-{max_revenue}" if min_revenue or max_revenue else None
                    },
                    "pagination": {
                        "page": page,
                        "limit": limit
                    },
                    "sorting": {
                        "sort_by": sort_by,
                        "sort_order": sort_order
                    }
                },
                "module_info": {
                    "api_module": "proposals.search",
                    "service": "ProposalSearchService",
                    "method": "search_proposals"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋提案時發生錯誤: {str(e)}")


@router.get("/search/full-text", response_model=Dict[str, Any])
async def full_text_search(
    q: str = Query(..., description="全文搜尋關鍵字"),
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    highlight: bool = Query(True, description="是否高亮關鍵字"),
    current_user = Depends(get_current_user_optional)
):
    """
    全文搜尋
    
    - **權限**: 公開搜尋
    - **功能**: 在提案內容中進行全文搜尋
    - **服務模組**: ProposalSearchService.full_text_search()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.full_text_search(
            query=q, 
            page=page, 
            limit=limit, 
            user_id=user_id,
            highlight=highlight
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "search_info": {
                    "query": q,
                    "highlight_enabled": highlight,
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "api_module": "proposals.search",
                    "service": "ProposalSearchService",
                    "method": "full_text_search"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"全文搜尋時發生錯誤: {str(e)}")


@router.get("/search/statistics", response_model=Dict[str, Any])
async def get_search_statistics():
    """
    取得搜尋統計
    
    - **權限**: 公開端點
    - **功能**: 提供搜尋相關的統計資訊
    - **服務模組**: ProposalSearchService.get_search_statistics()
    """
    try:
        stats = await proposal_service.search.get_search_statistics()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": stats,
                "module_info": {
                    "api_module": "proposals.search",
                    "service": "ProposalSearchService",
                    "method": "get_search_statistics"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得搜尋統計時發生錯誤: {str(e)}")


@router.post("/search/advanced", response_model=Dict[str, Any])
async def advanced_search(
    search_criteria: Dict[str, Any],
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    進階搜尋
    
    - **權限**: 公開搜尋，登入用戶可看更多內容
    - **功能**: 支援複雜的搜尋條件組合
    - **服務模組**: ProposalSearchService.advanced_search()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.advanced_search(
            search_criteria, page, limit, user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "search_criteria": search_criteria,
                "pagination": {
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "api_module": "proposals.search",
                    "service": "ProposalSearchService",
                    "method": "advanced_search"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"進階搜尋時發生錯誤: {str(e)}")


@router.get("/search/filter/industry/{industry}", response_model=Dict[str, Any])
async def filter_by_industry(
    industry: Industry,
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    按產業篩選
    
    - **權限**: 公開篩選
    - **功能**: 篩選特定產業的提案
    - **服務模組**: ProposalSearchService.filter_by_industry()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.filter_by_industry(
            industry, page, limit, user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "filter": {
                    "type": "industry",
                    "value": industry,
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "api_module": "proposals.search",
                    "service": "ProposalSearchService",
                    "method": "filter_by_industry"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產業篩選時發生錯誤: {str(e)}")


@router.get("/search/filter/size/{company_size}", response_model=Dict[str, Any])
async def filter_by_size(
    company_size: CompanySize,
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    按公司規模篩選
    
    - **權限**: 公開篩選
    - **功能**: 篩選特定規模的公司提案
    - **服務模組**: ProposalSearchService.filter_by_size()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.filter_by_size(
            company_size, page, limit, user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "filter": {
                    "type": "company_size",
                    "value": company_size,
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "api_module": "proposals.search",
                    "service": "ProposalSearchService",
                    "method": "filter_by_size"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"公司規模篩選時發生錯誤: {str(e)}")


@router.get("/search/filter/location/{location}", response_model=Dict[str, Any])
async def filter_by_location(
    location: str,
    page: int = Query(1, ge=1, description="頁數"),
    limit: int = Query(10, ge=1, le=50, description="每頁數量"),
    current_user = Depends(get_current_user_optional)
):
    """
    按地區篩選
    
    - **權限**: 公開篩選
    - **功能**: 篩選特定地區的提案
    - **服務模組**: ProposalSearchService.filter_by_location()
    """
    try:
        user_id = str(current_user.id) if current_user else None
        results = await proposal_service.search.filter_by_location(
            location, page, limit, user_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": results,
                "filter": {
                    "type": "location",
                    "value": location,
                    "page": page,
                    "limit": limit
                },
                "module_info": {
                    "api_module": "proposals.search",
                    "service": "ProposalSearchService",
                    "method": "filter_by_location"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"地區篩選時發生錯誤: {str(e)}")


@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_proposal_summary():
    """
    取得提案總覽
    
    - **權限**: 公開端點
    - **功能**: 取得提案系統的基本統計資訊
    - **服務模組**: ProposalSearchService + 統計組合
    """
    try:
        # 組合多個服務的統計資訊
        search_stats = await proposal_service.search.get_search_statistics()
        
        # 基本統計
        basic_stats = {
            "total_proposals": search_stats.get("total_proposals", 0),
            "active_proposals": search_stats.get("active_proposals", 0),
            "published_proposals": search_stats.get("published_proposals", 0),
            "pending_reviews": search_stats.get("pending_reviews", 0)
        }
        
        # 產業分布
        industry_distribution = search_stats.get("industry_distribution", {})
        
        # 規模分布
        size_distribution = search_stats.get("size_distribution", {})
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "basic_statistics": basic_stats,
                    "industry_distribution": industry_distribution,
                    "size_distribution": size_distribution,
                    "search_statistics": {
                        "total_searches_today": search_stats.get("searches_today", 0),
                        "popular_keywords": search_stats.get("popular_keywords", []),
                        "trending_industries": search_stats.get("trending_industries", [])
                    },
                    "system_status": "operational",
                    "last_updated": search_stats.get("last_updated", "now")
                },
                "module_info": {
                    "api_module": "proposals.search",
                    "services": ["ProposalSearchService", "統計組合"],
                    "method": "get_proposal_summary"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得提案總覽時發生錯誤: {str(e)}")


@router.get("/search/suggestions", response_model=Dict[str, Any])
async def get_search_suggestions(
    q: str = Query(..., min_length=1, description="搜尋關鍵字前綴"),
    limit: int = Query(10, ge=1, le=20, description="建議數量")
):
    """
    取得搜尋建議
    
    - **權限**: 公開端點
    - **功能**: 根據輸入提供搜尋關鍵字建議
    - **服務模組**: ProposalSearchService.get_search_suggestions()
    """
    try:
        suggestions = await proposal_service.search.get_search_suggestions(q, limit) if hasattr(proposal_service.search, 'get_search_suggestions') else {
            "keywords": [f"{q}科技", f"{q}製造", f"{q}服務"],
            "companies": [f"{q}公司", f"{q}企業"],
            "industries": []
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "query": q,
                    "suggestions": suggestions,
                    "limit": limit
                },
                "module_info": {
                    "api_module": "proposals.search",
                    "service": "ProposalSearchService",
                    "method": "get_search_suggestions"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得搜尋建議時發生錯誤: {str(e)}")