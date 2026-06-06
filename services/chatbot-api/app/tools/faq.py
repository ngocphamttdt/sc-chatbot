"""FAQ / knowledge-base lookup exposed to the LLM as a tool."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from app.core import analytics
from app.knowledge import vectorstore
from app.tenancy import TenantContext


def make_faq_tools(tenant: TenantContext):
    @tool
    def search_knowledge_base(query: str, k: int = 4) -> str:
        """Tra cứu kho tri thức của doanh nghiệp (FAQ, mô tả sản phẩm, chính sách).

        Dùng tool này khi khách hỏi về: thông tin doanh nghiệp, công dụng /
        thành phần / chống chỉ định sản phẩm, chính sách đổi trả, vận chuyển,
        khuyến mãi… Trả về các đoạn văn liên quan nhất.

        `query`: câu hỏi của khách (tiếng Việt). `k`: số đoạn cần lấy (mặc định 4).
        """
        docs = vectorstore.search(tenant, query, k=k)
        if not docs:
            return "Kho tri thức trống hoặc không tìm thấy đoạn phù hợp."
        analytics.track(tenant, "faq_hit", {"query": query, "hits": len(docs)})
        results = [
            {
                "source": d.metadata.get("source", "unknown"),
                "content": d.page_content,
            }
            for d in docs
        ]
        return json.dumps(results, ensure_ascii=False)

    return [search_knowledge_base]
