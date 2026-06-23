"""Function-calling tools assembled per tenant request."""
from __future__ import annotations

from typing import List

from langchain_core.tools import BaseTool

from app.tenancy import TenantContext
from app.tools.booking import make_booking_tools
from app.tools.faq import make_faq_tools
from app.tools.order import make_order_tools


def build_tools(tenant: TenantContext) -> List[BaseTool]:
    return [
        *make_faq_tools(tenant),
        *make_order_tools(tenant),
        *make_booking_tools(tenant),
    ]
