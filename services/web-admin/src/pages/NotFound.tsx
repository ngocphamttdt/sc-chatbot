import { useNavigate } from "react-router-dom";

export default function NotFound() {
  const nav = useNavigate();
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="text-6xl font-bold text-slate-200 mb-4">404</div>
      <h1 className="text-xl font-semibold text-slate-700 mb-2">Trang không tồn tại hoặc bạn không có quyền truy cập</h1>
      <p className="text-sm text-slate-400 mb-6">Vui lòng liên hệ quản trị viên nếu bạn cho rằng đây là lỗi.</p>
      <button
        onClick={() => nav(-1)}
        className="px-4 py-2 rounded border border-gray-300 text-sm text-slate-600 hover:bg-gray-50 transition"
      >
        Quay lại
      </button>
    </div>
  );
}
