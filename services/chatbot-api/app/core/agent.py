"""LangChain agent: tool-calling LLM + per-tenant tools + conversation memory.

Built on LangChain 1.x `create_agent` (LangGraph state graph under the hood).

Flow per turn:
1. Load chat history for (tenant, session).
2. Pull top-k snippets from the tenant knowledge base ("light RAG") and embed
   them into the system prompt - heavy lookups still go through the
   `search_knowledge_base` tool when the model decides it needs more.
3. Invoke the agent. It may call tools (FAQ search, products, orders, booking)
   in a loop until it produces a final answer.
4. Persist both sides of the turn into history and analytics.
"""
from __future__ import annotations

import time
from typing import Any

from langgraph.prebuilt import create_react_agent as create_agent
from langchain_core.messages import HumanMessage, SystemMessage

from app.admin import configs as admin_configs
from app.core import analytics, memory
from app.core.llm import get_chat_model
from app.knowledge import vectorstore
from app.tenancy import TenantContext
from app.tools import build_tools


# Header đặt trước phần ngữ cảnh RAG - dùng chung cho cả prompt mặc định lẫn tuỳ biến.
KB_CONTEXT_HEADER = "Ngữ cảnh liên quan từ kho tri thức (có thể trống):"

# Placeholder tenant được phép dùng trong prompt tuỳ biến - nguồn duy nhất, test import lại.
SUPPORTED_PLACEHOLDERS = frozenset({"tenant_name", "industry"})

SYSTEM_TEMPLATE = (
    """Bạn là trợ lý chăm sóc khách hàng AI của doanh nghiệp {tenant_name} (ngành: {industry}).

Nguyên tắc:
- Trả lời ngắn gọn, thân thiện, bằng tiếng Việt.
- Khi khách hỏi về sản phẩm / chính sách / FAQ -> dùng tool `search_knowledge_base` hoặc `get_product`.
- Khi khách muốn mua / đặt -> hỏi đủ thông tin rồi mới gọi `create_order` / `create_booking`.
  Bắt buộc: tên, số điện thoại, địa chỉ (đơn hàng) hoặc ngày, số khách (tour).
- Trước khi tạo đơn / booking, luôn kiểm tra tồn kho hoặc còn chỗ.
- Nếu không chắc, hãy hỏi lại thay vì bịa thông tin.
- Khi đã tạo đơn thành công, đọc to mã đơn cho khách và xác nhận lại tóm tắt.

"""
    + KB_CONTEXT_HEADER
    + "\n{kb_context}\n"
)


def _kb_context(tenant: TenantContext, query: str, k: int = 3) -> str:
    docs = vectorstore.search(tenant, query, k=k)
    if not docs:
        return "(chưa có)"
    return "\n---\n".join(d.page_content for d in docs)


def _render_custom_prompt(template: str, tenant: TenantContext) -> str:
    """Render the supported tenant placeholders without interpreting braces."""
    values = {"tenant_name": tenant.name, "industry": tenant.industry}
    for placeholder in SUPPORTED_PLACEHOLDERS:
        template = template.replace("{" + placeholder + "}", values[placeholder])
    return template


def _build_agent(tenant: TenantContext, kb_context: str):
    custom = admin_configs.get_prompt(tenant)
    if custom:
        system_prompt = (
            _render_custom_prompt(custom, tenant)
            + "\n\n"
            + KB_CONTEXT_HEADER
            + "\n"
            + kb_context
        )
    else:
        system_prompt = SYSTEM_TEMPLATE.format(
            tenant_name=tenant.name,
            industry=tenant.industry,
            kb_context=kb_context,
        )
    return create_agent(
        model=get_chat_model(),
        tools=build_tools(tenant),
        prompt=system_prompt,
    )


def _extract_reply(state: dict[str, Any]) -> str:
    """Pull the last AI text out of LangGraph agent state."""
    messages = state.get("messages", []) or []
    for m in reversed(messages):
        # AIMessage may carry text plus tool calls; we want the final text.
        if getattr(m, "type", None) == "ai" or type(m).__name__ == "AIMessage":
            content = m.content
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                # OpenAI tool-calling format: list of content blocks
                texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                joined = " ".join(t for t in texts if t).strip()
                if joined:
                    return joined
    return ""


def chat(tenant: TenantContext, session_id: str, user_message: str) -> dict[str, Any]:
    analytics.track(tenant, "message_in", {"session_id": session_id, "len": len(user_message)})
    started = time.perf_counter()

    history = memory.load_history(tenant, session_id, limit=20)
    kb = _kb_context(tenant, user_message)
    agent_graph = _build_agent(tenant, kb)

    # The new agent expects a message list and returns the full updated list.
    # We prepend history + a fresh user turn; the system prompt is baked in.
    input_messages = [*history, HumanMessage(content=user_message)]

    try:
        state = agent_graph.invoke({"messages": input_messages})
        reply = _extract_reply(state) or "Xin lỗi, em chưa rõ ý ạ."
        error = None
    except Exception as exc:  # noqa: BLE001
        reply = f"Hệ thống đang bận, vui lòng thử lại sau."
        error = f"{type(exc).__name__}: {exc}"

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    memory.append_turn(tenant, session_id, "user", user_message)
    memory.append_turn(tenant, session_id, "assistant", reply)
    analytics.track(tenant, "message_out", {"session_id": session_id, "len": len(reply)})
    analytics.track(tenant, "response_latency_ms", {"session_id": session_id, "ms": elapsed_ms})

    return {"reply": reply, "latency_ms": elapsed_ms, "error": error}
