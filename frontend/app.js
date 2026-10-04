// app.js - SGGo! District 5 Edition
// Tự động nhận diện môi trường Localhost hoặc Production (Render)
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000/api"
  : "https://sggo-backend.onrender.com/api";

let userChoices = {
  category: null,
  context: null,
  price_level: null
};

let allPlacesCache = [];

document.addEventListener("DOMContentLoaded", () => {
  preloadPlaces();
});

// Tải dữ liệu thực tế từ API Backend
async function preloadPlaces() {
  try {
    const res = await fetch(`${API_BASE}/places`);
    const data = await res.json();
    // Tương thích cả trường hợp Backend trả về mảng trực tiếp hoặc bọc trong { data: [...] }
    allPlacesCache = Array.isArray(data) ? data : (data.data || []);
    const countEl = document.getElementById("totalPlacesCount");
    if (countEl) countEl.innerText = allPlacesCache.length;
  } catch (e) {
    console.warn("Backend đang khởi động hoặc offline.");
  }
}

// Xử lý chọn từng bước
function selectAnswer(key, value, nextStep) {
  userChoices[key] = value;

  if (nextStep === 'finish') {
    showFinishResults();
  } else {
    document.querySelectorAll(".step-card").forEach(el => el.classList.add("hidden"));
    document.getElementById(`step${nextStep}`).classList.remove("hidden");
  }
}

function goBackStep(step) {
  document.querySelectorAll(".step-card").forEach(el => el.classList.add("hidden"));
  document.getElementById(`step${step}`).classList.remove("hidden");
}

function restartFlow() {
  userChoices = { category: null, context: null, price_level: null };
  document.querySelectorAll(".step-card").forEach(el => el.classList.add("hidden"));
  document.getElementById("step1").classList.remove("hidden");
}

// Hiển thị 3 kết quả tinh tuyển từ dữ liệu thật
function showFinishResults() {
  document.querySelectorAll(".step-card").forEach(el => el.classList.add("hidden"));
  const finishContainer = document.getElementById("stepFinish");
  finishContainer.classList.remove("hidden");

  const resultsBox = document.getElementById("flowResults");
  resultsBox.innerHTML = "";

  // Lọc quán theo category nếu người dùng chọn
  let matched = allPlacesCache.filter(p => !userChoices.category || p.category === userChoices.category);

  // Fallback nếu danh sách kết quả ít hơn 3
  if (matched.length === 0) {
    matched = allPlacesCache;
  }

  const selectedThree = matched.slice(0, 3);

  selectedThree.forEach((p, idx) => {
    const displayAddr = p.full_address && p.full_address !== "Đường đi" 
      ? p.full_address 
      : `${p.street ? p.street + ', ' : ''}${p.district || 'Quận 5'}, TP.HCM`;
    const reviews = p.reviews_count ? `(${p.reviews_count} đánh giá)` : '';

    resultsBox.innerHTML += `
      <div class="bg-white p-5 rounded-2xl border border-slate-200/80 hover:border-[#FF5733] hover:shadow-md hover:shadow-[#FF5733]/5 transition-all">
        <div class="flex justify-between items-start">
          <div>
            <span class="text-[10px] font-extrabold uppercase tracking-wider text-[#FF5733] bg-[#FF5733]/10 px-2 py-0.5 rounded-md">
              Gợi ý ${idx + 1} • ${p.district || 'Quận 5'}
            </span>
            <h3 class="font-extrabold text-slate-900 text-lg mt-1.5">${p.name}</h3>
          </div>
          <span class="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-1 rounded-xl font-bold">
            ⭐ ${p.rating || 4.2} <span class="text-[10px] font-normal text-slate-500">${reviews}</span>
          </span>
        </div>
        <p class="text-xs text-slate-500 mt-2 flex items-center gap-1.5">
          <i class="fa-solid fa-location-dot text-red-400"></i> ${displayAddr}
        </p>
        <div class="flex items-center gap-3 mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500">
          <span class="font-bold text-slate-700">Loại hình: ${p.osm_type || 'Ẩm thực'}</span>
          <span>•</span>
          <span class="font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">Tọa độ: ${p.lat ? p.lat.toFixed(4) : ''}, ${p.lon ? p.lon.toFixed(4) : ''}</span>
        </div>
      </div>
    `;
  });
}

// Chuyển Tab
function switchMode(mode) {
  document.getElementById("viewFlow").classList.toggle("hidden", mode !== "flow");
  document.getElementById("viewAI").classList.toggle("hidden", mode !== "ai");
  document.getElementById("viewAll").classList.toggle("hidden", mode !== "all");

  const tabs = {
    flow: document.getElementById("navFlow"),
    ai: document.getElementById("navAI"),
    all: document.getElementById("navAll")
  };

  Object.keys(tabs).forEach(k => {
    tabs[k].className = (k === mode) ? "tab-pill active" : "tab-pill";
  });

  if (mode === "all") renderAllPlaces();
}

// Render toàn bộ quán thực tế ở tab "Địa Điểm"
function renderAllPlaces() {
  const container = document.getElementById("allPlacesGrid");
  container.innerHTML = "";

  allPlacesCache.forEach(p => {
    const isEat = p.category === 'an_uong';
    const displayAddr = p.full_address && p.full_address !== "Đường đi" 
      ? p.full_address 
      : `${p.street ? p.street + ', ' : ''}${p.district || 'Quận 5'}, TP.HCM`;
    const reviews = p.reviews_count ? `(${p.reviews_count})` : '';

    container.innerHTML += `
      <div class="p-4 bg-white border border-slate-200/80 rounded-2xl text-xs hover:border-[#FF5733]/50 transition">
        <div class="flex justify-between items-start font-bold text-slate-800">
          <h4 class="text-sm font-extrabold">${p.name}</h4>
          <span class="text-amber-600 font-bold">⭐ ${p.rating || 4.0} <span class="text-[10px] text-slate-400">${reviews}</span></span>
        </div>
        <p class="text-slate-500 mt-1">📍 ${displayAddr}</p>
        <div class="flex justify-between items-center mt-3 pt-2.5 border-t border-slate-100 text-[11px]">
          <span class="px-2 py-0.5 rounded-md ${isEat ? 'bg-orange-50 text-[#FF5733]' : 'bg-sky-50 text-sky-600'} font-semibold">
            ${isEat ? '🍕 Ăn uống' : '🛹 Đi chơi'} • ${p.district || 'Quận 5'}
          </span>
          <span class="font-mono text-slate-400">${p.osm_type || 'quán ăn'}</span>
        </div>
      </div>
    `;
  });
}

// Gọi API Gemini lập lịch trình
async function requestAIItinerary() {
  const btn = document.getElementById("btnSubmitAI");
  const container = document.getElementById("aiTimeline");
  const summary = document.getElementById("aiSummary");

  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang tối ưu cung đường...`;
  btn.disabled = true;

  const payload = {
    start_location: document.getElementById("aiStartLoc").value,
    free_time: document.getElementById("aiTime").value,
    context: document.getElementById("aiContext").value,
    budget: "Vừa vặn thoải mái"
  };

  try {
    const res = await fetch(`${API_BASE}/ai-itinerary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    summary.innerText = result.summary || "Lộ trình tối ưu do AI sắp xếp";
    container.innerHTML = "";

    result.steps.forEach(s => {
      container.innerHTML += `
        <div class="timeline-item">
          <div class="timeline-dot"></div>
          <div class="bg-slate-50 p-4 rounded-2xl border border-slate-200/80 text-xs">
            <span class="font-bold text-[#FF5733] tracking-wide">${s.time}</span>
            <h5 class="font-extrabold text-slate-800 text-sm mt-1">${s.action} — ${s.location}</h5>
            <p class="text-slate-500 mt-1">🛵 Di chuyển: <strong>${s.travel_info}</strong></p>
            ${s.traffic_warning ? `<p class="text-amber-700 bg-amber-50 border border-amber-200 p-2 rounded-xl mt-2 font-medium">⚠️ ${s.traffic_warning}</p>` : ''}
          </div>
        </div>
      `;
    });
  } catch (err) {
    container.innerHTML = `<div class="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl text-xs">Chưa thể kết nối tới Backend. Hãy chắc chắn server local hoặc Render đang hoạt động.</div>`;
  } finally {
    btn.innerHTML = `<span>Lên Lộ Trình Ngay</span> <i class="fa-solid fa-arrow-right text-xs"></i>`;
    btn.disabled = false;
  }
}

function triggerAuthPlaceholder() {
  alert("🔐 [Kiến Trúc Giai Đoạn 2]: Chức năng Đăng ký / Đăng nhập tài khoản & Lưu danh sách quán yêu thích vào Database sẽ được hoàn thiện sau khi nhóm duyệt đề tài.");
}

function triggerAdminPlaceholder() {
  alert("⚙️️ [Kiến Trúc Giai Đoạn 2]: Trang Dashboard Quản trị viên (Thêm, Sửa, Xóa, Duyệt quán vào cơ sở dữ liệu) dành cho Admin.");
}