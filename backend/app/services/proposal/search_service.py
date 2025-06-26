"""
提案搜尋服務 - Search Service
負責提案的搜尋、篩選、排序和分頁功能
支援多維度搜尋和智能篩選
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
import re
from math import ceil

from app.core.database import Database
from app.core.exceptions import BusinessException, ValidationException
from app.models.proposal import Proposal, ProposalStatus, Industry, CompanySize
from app.schemas.proposal import ProposalSearchParams


class ProposalSearchService:
    """提案搜尋服務類 - 搜尋和篩選功能"""
    
    def __init__(self):
        """初始化搜尋服務"""
        self.database = None
        
    async def _get_database(self) -> AsyncIOMotorDatabase:
        """取得資料庫實例"""
        if self.database is None:
            self.database = Database.get_database()
        return self.database
    
    async def _get_collection(self) -> AsyncIOMotorCollection:
        """取得提案集合"""
        database = await self._get_database()
        return database.proposals
    
    # ==================== 主要搜尋接口 ====================
    
    async def search_proposals(
        self, 
        search_params: ProposalSearchParams,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        搜尋提案 - 主要搜尋接口
        
        Args:
            search_params: 搜尋參數
            user_id: 搜尋者 ID (用於權限控制)
            
        Returns:
            Dict[str, Any]: 搜尋結果
                - proposals: 提案列表
                - total_count: 總數量
                - page_info: 分頁資訊
                - filters_applied: 已應用的篩選器
                - suggestions: 搜尋建議
        """
        try:
            collection = await self._get_collection()
            
            # 建構基礎查詢
            base_query = await self._build_base_query(search_params, user_id)
            
            # 建構篩選條件
            filter_query = await self._build_filter_query(search_params)
            
            # 合併查詢條件
            final_query = {**base_query, **filter_query}
            
            # 建構排序條件
            sort_criteria = self._build_sort_criteria(search_params.sort_by, search_params.sort_order)
            
            # 計算總數量
            total_count = await collection.count_documents(final_query)
            
            # 計算分頁
            page_info = self._calculate_pagination(
                page=search_params.page,
                page_size=search_params.page_size,
                total_count=total_count
            )
            
            # 執行搜尋查詢
            cursor = collection.find(final_query).sort(sort_criteria)
            cursor = cursor.skip(page_info["offset"]).limit(page_info["page_size"])
            
            # 轉換結果
            proposals = []
            async for proposal_dict in cursor:
                proposal = Proposal.from_dict(proposal_dict)
                # 根據用戶權限決定返回的資料層級
                proposal_data = await self._format_proposal_for_search(proposal, user_id)
                proposals.append(proposal_data)
            
            # 生成搜尋建議
            suggestions = await self._generate_search_suggestions(search_params, total_count)
            
            return {
                "proposals": proposals,
                "total_count": total_count,
                "page_info": page_info,
                "filters_applied": self._get_applied_filters(search_params),
                "suggestions": suggestions,
                "search_metadata": {
                    "query_time": datetime.utcnow(),
                    "search_terms": search_params.keywords,
                    "result_count": len(proposals)
                }
            }
            
        except Exception as e:
            raise BusinessException(
                message=f"搜尋提案時發生錯誤: {str(e)}",
                error_code="PROPOSAL_SEARCH_ERROR"
            )
    
    async def full_text_search(
        self, 
        keywords: str, 
        limit: int = 20,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        全文搜尋
        
        Args:
            keywords: 搜尋關鍵字
            limit: 結果數量限制
            user_id: 搜尋者 ID
            
        Returns:
            List[Dict[str, Any]]: 搜尋結果 (包含相關性分數)
        """
        try:
            collection = await self._get_collection()
            
            # 建構文字搜尋查詢
            text_query = {
                "$text": {"$search": keywords},
                "status": {"$in": [ProposalStatus.AVAILABLE, ProposalStatus.SENT]}
            }
            
            # 執行文字搜尋 (包含分數)
            cursor = collection.find(
                text_query,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            results = []
            async for doc in cursor:
                proposal = Proposal.from_dict(doc)
                result = {
                    "proposal": await self._format_proposal_for_search(proposal, user_id),
                    "relevance_score": doc.get("score", 0),
                    "matched_fields": await self._identify_matched_fields(proposal, keywords)
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            raise BusinessException(
                message=f"全文搜尋時發生錯誤: {str(e)}",
                error_code="FULL_TEXT_SEARCH_ERROR"
            )
    
    # ==================== 進階篩選功能 ====================
    
    async def filter_by_industry(
        self, 
        industries: List[Industry],
        additional_filters: Optional[Dict] = None
    ) -> List[Proposal]:
        """
        按行業篩選提案
        
        Args:
            industries: 行業列表
            additional_filters: 額外篩選條件
            
        Returns:
            List[Proposal]: 篩選結果
        """
        try:
            collection = await self._get_collection()
            
            query = {
                "company_info.industry": {"$in": industries},
                "status": {"$in": [ProposalStatus.AVAILABLE, ProposalStatus.SENT]}
            }
            
            if additional_filters:
                query.update(additional_filters)
            
            cursor = collection.find(query).sort("created_at", -1)
            
            proposals = []
            async for proposal_dict in cursor:
                proposals.append(Proposal.from_dict(proposal_dict))
            
            return proposals
            
        except Exception as e:
            raise BusinessException(
                message=f"按行業篩選時發生錯誤: {str(e)}",
                error_code="INDUSTRY_FILTER_ERROR"
            )
    
    async def filter_by_size(
        self, 
        min_revenue: Optional[float] = None,
        max_revenue: Optional[float] = None,
        company_sizes: Optional[List[CompanySize]] = None
    ) -> List[Proposal]:
        """
        按公司規模篩選提案
        
        Args:
            min_revenue: 最小營收
            max_revenue: 最大營收
            company_sizes: 公司規模列表
            
        Returns:
            List[Proposal]: 篩選結果
        """
        try:
            collection = await self._get_collection()
            
            query = {
                "status": {"$in": [ProposalStatus.AVAILABLE, ProposalStatus.SENT]}
            }
            
            # 營收範圍篩選
            revenue_filter = {}
            if min_revenue is not None:
                revenue_filter["$gte"] = min_revenue
            if max_revenue is not None:
                revenue_filter["$lte"] = max_revenue
            
            if revenue_filter:
                query["financial_info.revenue"] = revenue_filter
            
            # 公司規模篩選
            if company_sizes:
                query["company_info.company_size"] = {"$in": company_sizes}
            
            cursor = collection.find(query).sort("financial_info.revenue", -1)
            
            proposals = []
            async for proposal_dict in cursor:
                proposals.append(Proposal.from_dict(proposal_dict))
            
            return proposals
            
        except Exception as e:
            raise BusinessException(
                message=f"按規模篩選時發生錯誤: {str(e)}",
                error_code="SIZE_FILTER_ERROR"
            )
    
    async def filter_by_location(
        self, 
        locations: List[str],
        radius_km: Optional[int] = None
    ) -> List[Proposal]:
        """
        按地理位置篩選提案
        
        Args:
            locations: 位置列表
            radius_km: 搜尋半徑 (公里，預留功能)
            
        Returns:
            List[Proposal]: 篩選結果
        """
        try:
            collection = await self._get_collection()
            
            # 建構位置查詢 (支援模糊匹配)
            location_patterns = [re.compile(loc, re.IGNORECASE) for loc in locations]
            
            query = {
                "company_info.headquarters": {"$in": location_patterns},
                "status": {"$in": [ProposalStatus.AVAILABLE, ProposalStatus.SENT]}
            }
            
            cursor = collection.find(query).sort("created_at", -1)
            
            proposals = []
            async for proposal_dict in cursor:
                proposals.append(Proposal.from_dict(proposal_dict))
            
            return proposals
            
        except Exception as e:
            raise BusinessException(
                message=f"按位置篩選時發生錯誤: {str(e)}",
                error_code="LOCATION_FILTER_ERROR"
            )
    
    # ==================== 排序功能 ====================
    
    async def sort_by_relevance(
        self, 
        proposals: List[Proposal], 
        search_terms: Optional[str] = None
    ) -> List[Proposal]:
        """
        按相關性排序
        
        Args:
            proposals: 提案列表
            search_terms: 搜尋詞 (用於計算相關性)
            
        Returns:
            List[Proposal]: 排序後的提案列表
        """
        if not search_terms:
            return proposals
        
        # 計算相關性分數並排序
        scored_proposals = []
        for proposal in proposals:
            score = self._calculate_relevance_score(proposal, search_terms)
            scored_proposals.append((proposal, score))
        
        # 按分數降序排序
        scored_proposals.sort(key=lambda x: x[1], reverse=True)
        
        return [proposal for proposal, score in scored_proposals]
    
    async def sort_by_date(
        self, 
        proposals: List[Proposal], 
        ascending: bool = False
    ) -> List[Proposal]:
        """
        按日期排序
        
        Args:
            proposals: 提案列表
            ascending: 是否升序 (False 為降序，即最新的在前)
            
        Returns:
            List[Proposal]: 排序後的提案列表
        """
        return sorted(
            proposals, 
            key=lambda p: p.created_at, 
            reverse=not ascending
        )
    
    async def sort_by_popularity(self, proposals: List[Proposal]) -> List[Proposal]:
        """
        按熱門程度排序 (基於瀏覽量)
        
        Args:
            proposals: 提案列表
            
        Returns:
            List[Proposal]: 排序後的提案列表
        """
        return sorted(
            proposals, 
            key=lambda p: p.view_count, 
            reverse=True
        )
    
    # ==================== 分頁功能 ====================
    
    async def paginate_results(
        self, 
        query: Dict[str, Any],
        page: int = 1,
        page_size: int = 20,
        sort_criteria: Optional[List[Tuple[str, int]]] = None
    ) -> Dict[str, Any]:
        """
        分頁處理搜尋結果
        
        Args:
            query: 查詢條件
            page: 頁碼 (從 1 開始)
            page_size: 每頁大小
            sort_criteria: 排序條件
            
        Returns:
            Dict[str, Any]: 分頁結果
        """
        try:
            collection = await self._get_collection()
            
            # 計算總數量
            total_count = await collection.count_documents(query)
            
            # 計算分頁資訊
            page_info = self._calculate_pagination(page, page_size, total_count)
            
            # 執行查詢
            cursor = collection.find(query)
            
            if sort_criteria:
                cursor = cursor.sort(sort_criteria)
            
            cursor = cursor.skip(page_info["offset"]).limit(page_info["page_size"])
            
            # 轉換結果
            proposals = []
            async for proposal_dict in cursor:
                proposals.append(Proposal.from_dict(proposal_dict))
            
            return {
                "data": proposals,
                "pagination": page_info,
                "total_count": total_count
            }
            
        except Exception as e:
            raise BusinessException(
                message=f"分頁處理時發生錯誤: {str(e)}",
                error_code="PAGINATION_ERROR"
            )
    
    # ==================== 統計和分析 ====================
    
    async def get_search_statistics(
        self, 
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        取得搜尋統計資訊
        
        Args:
            date_from: 開始日期
            date_to: 結束日期
            
        Returns:
            Dict[str, Any]: 統計資訊
        """
        try:
            collection = await self._get_collection()
            
            # 建構日期範圍查詢
            date_query = {}
            if date_from or date_to:
                date_range = {}
                if date_from:
                    date_range["$gte"] = date_from
                if date_to:
                    date_range["$lte"] = date_to
                date_query["created_at"] = date_range
            
            # 聚合統計
            pipeline = [
                {"$match": {**date_query, "status": {"$ne": ProposalStatus.ARCHIVED}}},
                {
                    "$group": {
                        "_id": None,
                        "total_proposals": {"$sum": 1},
                        "available_proposals": {
                            "$sum": {"$cond": [{"$eq": ["$status", ProposalStatus.AVAILABLE]}, 1, 0]}
                        },
                        "avg_view_count": {"$avg": "$view_count"},
                        "industries": {"$addToSet": "$company_info.industry"},
                        "locations": {"$addToSet": "$company_info.headquarters"}
                    }
                }
            ]
            
            result = await collection.aggregate(pipeline).to_list(1)
            
            if not result:
                return {
                    "total_proposals": 0,
                    "available_proposals": 0,
                    "avg_view_count": 0,
                    "unique_industries": 0,
                    "unique_locations": 0
                }
            
            stats = result[0]
            return {
                "total_proposals": stats.get("total_proposals", 0),
                "available_proposals": stats.get("available_proposals", 0),
                "avg_view_count": round(stats.get("avg_view_count", 0), 2),
                "unique_industries": len(stats.get("industries", [])),
                "unique_locations": len(stats.get("locations", [])),
                "popular_industries": stats.get("industries", []),
                "popular_locations": stats.get("locations", [])
            }
            
        except Exception as e:
            raise BusinessException(
                message=f"取得搜尋統計時發生錯誤: {str(e)}",
                error_code="SEARCH_STATISTICS_ERROR"
            )
    
    # ==================== 私有輔助方法 ====================
    
    async def _build_base_query(
        self, 
        search_params: ProposalSearchParams,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """建構基礎查詢條件"""
        query = {}
        
        # 基本狀態篩選 (只搜尋可見的提案)
        if user_id:
            # 如果是登入用戶，可以看到更多狀態的提案
            query["status"] = {"$in": [
                ProposalStatus.AVAILABLE, 
                ProposalStatus.SENT
            ]}
        else:
            # 匿名用戶只能看到公開可用的提案
            query["status"] = ProposalStatus.AVAILABLE
        
        # 關鍵字搜尋
        if search_params.keywords:
            query["$text"] = {"$search": search_params.keywords}
        
        return query
    
    async def _build_filter_query(self, search_params: ProposalSearchParams) -> Dict[str, Any]:
        """建構篩選查詢條件"""
        filter_query = {}
        
        # 行業篩選
        if search_params.industries:
            filter_query["company_info.industry"] = {"$in": search_params.industries}
        
        # 公司規模篩選
        if search_params.company_sizes:
            filter_query["company_info.company_size"] = {"$in": search_params.company_sizes}
        
        # 營收範圍篩選
        if search_params.min_revenue is not None or search_params.max_revenue is not None:
            revenue_filter = {}
            if search_params.min_revenue is not None:
                revenue_filter["$gte"] = search_params.min_revenue
            if search_params.max_revenue is not None:
                revenue_filter["$lte"] = search_params.max_revenue
            filter_query["financial_info.revenue"] = revenue_filter
        
        # 地點篩選
        if search_params.locations:
            location_patterns = [
                re.compile(loc, re.IGNORECASE) for loc in search_params.locations
            ]
            filter_query["company_info.headquarters"] = {"$in": location_patterns}
        
        # 成立年份範圍
        if search_params.min_established_year or search_params.max_established_year:
            year_filter = {}
            if search_params.min_established_year:
                year_filter["$gte"] = search_params.min_established_year
            if search_params.max_established_year:
                year_filter["$lte"] = search_params.max_established_year
            filter_query["company_info.established_year"] = year_filter
        
        return filter_query
    
    def _build_sort_criteria(
        self, 
        sort_by: Optional[str] = None, 
        sort_order: Optional[str] = None
    ) -> List[Tuple[str, int]]:
        """建構排序條件"""
        order = 1 if sort_order == "asc" else -1
        
        sort_mapping = {
            "created_at": [("created_at", order)],
            "updated_at": [("updated_at", order)],
            "view_count": [("view_count", order)],
            "revenue": [("financial_info.revenue", order)],
            "company_name": [("company_info.company_name", order)],
            "relevance": [("score", {"$meta": "textScore"})]  # 文字搜尋相關性
        }
        
        return sort_mapping.get(sort_by, [("created_at", -1)])  # 預設按建立時間降序
    
    def _calculate_pagination(
        self, 
        page: int, 
        page_size: int, 
        total_count: int
    ) -> Dict[str, Any]:
        """計算分頁資訊"""
        page = max(1, page)  # 確保頁碼至少為 1
        page_size = min(max(1, page_size), 100)  # 限制每頁大小在 1-100 之間
        
        total_pages = ceil(total_count / page_size) if total_count > 0 else 1
        offset = (page - 1) * page_size
        
        return {
            "current_page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_count": total_count,
            "offset": offset,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None
        }
    
    async def _format_proposal_for_search(
        self, 
        proposal: Proposal, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """格式化提案用於搜尋結果顯示"""
        # 基本公開資訊
        result = {
            "id": str(proposal.id),
            "company_info": {
                "industry": proposal.company_info.industry,
                "company_size": proposal.company_info.company_size,
                "headquarters": proposal.company_info.headquarters,
                "established_year": proposal.company_info.established_year
            },
            "teaser_content": proposal.teaser_content.dict(),
            "status": proposal.status,
            "view_count": proposal.view_count,
            "created_at": proposal.created_at
        }
        
        # 根據用戶權限添加更多資訊
        if user_id:
            # 登入用戶可以看到更多資訊
            result["financial_summary"] = {
                "revenue_range": self._get_revenue_range(proposal.financial_info.revenue),
                "has_profit_data": proposal.financial_info.profit is not None
            }
        
        return result
    
    def _get_revenue_range(self, revenue: Optional[float]) -> str:
        """取得營收範圍描述"""
        if revenue is None:
            return "未提供"
        
        if revenue < 1_000_000:
            return "< 100萬"
        elif revenue < 10_000_000:
            return "100萬 - 1000萬"
        elif revenue < 100_000_000:
            return "1000萬 - 1億"
        else:
            return "> 1億"
    
    def _calculate_relevance_score(self, proposal: Proposal, search_terms: str) -> float:
        """計算提案與搜尋詞的相關性分數"""
        score = 0.0
        terms = search_terms.lower().split()
        
        # 檢查公司名稱匹配
        company_name = proposal.company_info.company_name.lower()
        for term in terms:
            if term in company_name:
                score += 2.0
        
        # 檢查業務概述匹配
        business_overview = proposal.teaser_content.business_overview.lower()
        for term in terms:
            if term in business_overview:
                score += 1.0
        
        # 檢查行業匹配
        industry = proposal.company_info.industry.lower()
        for term in terms:
            if term in industry:
                score += 1.5
        
        return score
    
    async def _identify_matched_fields(
        self, 
        proposal: Proposal, 
        search_terms: str
    ) -> List[str]:
        """識別匹配的欄位"""
        matched_fields = []
        terms = search_terms.lower().split()
        
        # 檢查各個欄位是否匹配
        fields_to_check = {
            "company_name": proposal.company_info.company_name.lower(),
            "business_overview": proposal.teaser_content.business_overview.lower(),
            "industry": proposal.company_info.industry.lower(),
            "headquarters": proposal.company_info.headquarters.lower()
        }
        
        for field, content in fields_to_check.items():
            for term in terms:
                if term in content and field not in matched_fields:
                    matched_fields.append(field)
                    break
        
        return matched_fields
    
    async def _generate_search_suggestions(
        self, 
        search_params: ProposalSearchParams, 
        result_count: int
    ) -> List[str]:
        """生成搜尋建議"""
        suggestions = []
        
        # 如果結果太少，提供建議
        if result_count < 5:
            if search_params.keywords:
                suggestions.append("嘗試使用更通用的關鍵字")
                suggestions.append("減少篩選條件以獲得更多結果")
            
            if search_params.industries and len(search_params.industries) == 1:
                suggestions.append("嘗試選擇多個相關行業")
            
            if search_params.min_revenue or search_params.max_revenue:
                suggestions.append("調整營收範圍篩選條件")
        
        # 如果結果太多，提供精確化建議
        elif result_count > 50:
            suggestions.append("添加更多篩選條件以精確化搜尋")
            suggestions.append("使用更具體的關鍵字")
        
        return suggestions
    
    def _get_applied_filters(self, search_params: ProposalSearchParams) -> Dict[str, Any]:
        """取得已應用的篩選器"""
        applied = {}
        
        if search_params.keywords:
            applied["keywords"] = search_params.keywords
        
        if search_params.industries:
            applied["industries"] = search_params.industries
        
        if search_params.company_sizes:
            applied["company_sizes"] = search_params.company_sizes
        
        if search_params.locations:
            applied["locations"] = search_params.locations
        
        if search_params.min_revenue is not None:
            applied["min_revenue"] = search_params.min_revenue
        
        if search_params.max_revenue is not None:
            applied["max_revenue"] = search_params.max_revenue
        
        return applied