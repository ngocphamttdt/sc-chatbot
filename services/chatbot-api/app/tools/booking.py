"""Booking tools - illustrates Function Calling for travel/tour scenarios.

Mock APIs simulate availability checks ("còn/hết vé"), pricing, and booking
creation. The agent should ask the user for missing fields before calling.
"""
from __future__ import annotations

import json
import time
import uuid

from langchain_core.tools import tool
from tinydb import Query, TinyDB

from app.core import analytics
from app.tenancy import TenantContext


def _bookings_db(tenant: TenantContext) -> TinyDB:
    return TinyDB(tenant.bookings_db)


# Mock tour catalog - in production this would come from a real ERP/API.
_MOCK_TOURS = {
    "DN3N2D": {"name": "Đà Nẵng 3N2Đ", "price_per_pax": 3500000, "capacity_per_day": 20},
    "PQ4N3D": {"name": "Phú Quốc 4N3Đ", "price_per_pax": 5200000, "capacity_per_day": 15},
    "HN2N1D": {"name": "Hà Nội 2N1Đ", "price_per_pax": 1800000, "capacity_per_day": 25},
}


def _booked_count(tenant: TenantContext, tour_code: str, date: str) -> int:
    Bk = Query()
    with _bookings_db(tenant) as db:
        rows = db.search((Bk.tour_code == tour_code) & (Bk.date == date))
    return sum(int(r.get("pax", 0)) for r in rows)


def make_booking_tools(tenant: TenantContext):
    @tool
    def check_tour_availability(tour_code: str, date: str, pax: int) -> str:
        """Kiểm tra còn/hết vé cho một tour theo ngày khởi hành và số lượng khách.

        `tour_code`: mã tour (ví dụ DN3N2D).
        `date`: ngày khởi hành định dạng YYYY-MM-DD.
        `pax`: số khách cần đặt.
        """
        tour = _MOCK_TOURS.get(tour_code.upper())
        if not tour:
            return f"Không tìm thấy tour {tour_code}. Các mã hợp lệ: {list(_MOCK_TOURS)}"
        booked = _booked_count(tenant, tour_code.upper(), date)
        remaining = tour["capacity_per_day"] - booked
        ok = remaining >= pax
        return json.dumps(
            {
                "tour_code": tour_code.upper(),
                "tour_name": tour["name"],
                "date": date,
                "remaining_seats": remaining,
                "available": ok,
                "total_price": tour["price_per_pax"] * pax if ok else None,
            },
            ensure_ascii=False,
        )

    @tool
    def create_booking(
        tour_code: str,
        date: str,
        pax: int,
        customer_name: str,
        phone: str,
    ) -> str:
        """Tạo booking tour. Yêu cầu đủ: tour_code, date, pax, customer_name, phone.

        Trước khi gọi tool này, AI phải đảm bảo tour còn chỗ (gọi
        `check_tour_availability`). Trả về booking_id.
        """
        tour_code = tour_code.upper()
        tour = _MOCK_TOURS.get(tour_code)
        if not tour:
            return f"Không tìm thấy tour {tour_code}."
        booked = _booked_count(tenant, tour_code, date)
        if tour["capacity_per_day"] - booked < pax:
            return "Tour đã hết chỗ cho ngày này, vui lòng chọn ngày khác."

        booking_id = "BK-" + uuid.uuid4().hex[:8].upper()
        record = {
            "booking_id": booking_id,
            "tour_code": tour_code,
            "tour_name": tour["name"],
            "date": date,
            "pax": pax,
            "total_price": tour["price_per_pax"] * pax,
            "customer": {"name": customer_name, "phone": phone},
            "created_at": time.time(),
            "status": "confirmed",
        }
        with _bookings_db(tenant) as db:
            db.insert(record)
        analytics.track(tenant, "booking_created", {"booking_id": booking_id})
        return json.dumps(
            {"booking_id": booking_id, "total_price": record["total_price"], "status": "confirmed"},
            ensure_ascii=False,
        )

    return [check_tour_availability, create_booking]
