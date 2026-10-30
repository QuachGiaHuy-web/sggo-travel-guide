// -*- coding: utf-8 -*-
/**
 * app.js - XỬ LÝ TOÀN BỘ LOGIC GIAO DIỆN SGGO! TRAVEL GUIDE
 * Môn học: Công nghệ Phần mềm (COMP1044)
 * 
 * Các nâng cấp mới nhất:
 * 1. Thanh tóm tắt lựa chọn (Breadcrumb bar) xem lại những gì đã chọn
 * 2. Mở rộng 5 mức ngân sách + Tự nhập số tiền mong muốn
 * 3. Hiển thị bình luận 5 sao & Lưu ý giờ cao điểm trực tiếp lên từng thẻ quán
 * 4. Bộ lọc Admin từ A đến Z (Tên, Thể loại, Số sao, Mức giá)
 * 5. Bóc tách tự động thông tin từ link Google Maps
 * 6. Cho phép chỉnh sửa URL ảnh và xem trước ảnh trực tiếp
 */

const API_BASE = window.location.protocol === "file:"
  ? "http://127.0.0.1:8000/api"
  : "/api";

let currentUser = null;
let currentFlowOffset = 0;
let userChoices = { 
  category: null, 
  context: null, 
  price_level: null,
  custom_budget: null 
};
let allPlacesCache = [];
let csvToUploadText = "";
let aiCompanion = "ban_be";
let aiPurpose = "ca_hai";
let drawerMap = null;
let drawerMarker = null;

document.addEventListener("DOMContentLoaded", () => {
  loadSavedUser();
  preloadPlaces();
  updateSelectionSummaryUI();
});

// ==============================================================================
// 1. QUẢN LÝ TÀI KHOẢN & PHÂN QUYỀN (AUTH)
// ==============================================================================

function loadSavedUser() {
  const saved = localStorage.getItem("sggo_current_user");
  if (saved) {
    try {
      currentUser = JSON.parse(saved);
      updateAuthUI();
    } catch (e) {
      localStorage.removeItem("sggo_current_user");
      currentUser = null;
      updateAuthUI();
    }
  } else {
    currentUser = null;
    updateAuthUI();
  }
}

function updateAuthUI() {
  const authContainer = document.getElementById("authContainer");
  const navAdmin = document.getElementById("navAdmin");
  const viewAdmin = document.getElementById("viewAdmin");

  if (currentUser && currentUser.role === "admin") {
    // CHỈ TÀI KHOẢN ADMIN MỚI ĐƯỢC HIỆN NÚT ADMIN
    authContainer.innerHTML = `
      <div class="flex items-center gap-1.5 bg-rose-50 border border-rose-200/90 px-2.5 py-1 rounded-xl shadow-sm whitespace-nowrap">
        <span class="w-2 h-2 rounded-full bg-rose-500 animate-pulse flex-shrink-0"></span>
        <span class="text-xs font-black text-rose-700">Admin</span>
        <button onclick="handleLogout()" title="Đăng xuất" class="ml-1 text-[11px] font-bold px-2 py-0.5 rounded-lg bg-rose-100 hover:bg-rose-200 text-rose-700 transition flex items-center gap-1">
          <i class="fa-solid fa-arrow-right-from-bracket text-[10px]"></i> Thoát
        </button>
      </div>
    `;
    if (navAdmin) {
      navAdmin.classList.remove("hidden");
      navAdmin.style.setProperty("display", "inline-flex", "important");
    }
  } else if (currentUser) {
    // NGƯỜI DÙNG THƯỜNG -> ẨN TUYỆT ĐỐI NÚT ADMIN
    authContainer.innerHTML = `
      <div class="flex items-center gap-1.5 bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-xl shadow-sm whitespace-nowrap">
        <span class="text-xs font-bold text-slate-800 truncate max-w-[90px]">👤 ${currentUser.username || 'User'}</span>
        <button onclick="handleLogout()" title="Đăng xuất" class="ml-1 text-[11px] font-bold px-2 py-0.5 rounded-lg bg-white hover:bg-rose-50 text-slate-600 hover:text-[#E11D48] border border-slate-200 transition flex items-center gap-1">
          <i class="fa-solid fa-arrow-right-from-bracket text-[10px]"></i> Thoát
        </button>
      </div>
    `;
    if (navAdmin) {
      navAdmin.classList.add("hidden");
      navAdmin.style.setProperty("display", "none", "important");
    }
    if (viewAdmin && !viewAdmin.classList.contains("hidden")) {
      switchMode("flow");
    }
  } else {
    // CHƯA ĐĂNG NHẬP (KHÁCH VÃNG LAI) -> ẨN TUYỆT ĐỐI NÚT ADMIN
    authContainer.innerHTML = `
      <button onclick="openAuthModal()" id="btnAuth" class="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 shadow-sm transition flex items-center gap-1.5 whitespace-nowrap flex-shrink-0">
        <i class="fa-regular fa-user text-slate-400"></i>
        <span>Đăng nhập</span>
      </button>
    `;
    if (navAdmin) {
      navAdmin.classList.add("hidden");
      navAdmin.style.setProperty("display", "none", "important");
    }
    if (viewAdmin && !viewAdmin.classList.contains("hidden")) {
      switchMode("flow");
    }
  }

  // Cập nhật lại danh sách quán để hiện / ẩn nút "Sửa quán (Admin)" ngay lập tức
  if (allPlacesCache && allPlacesCache.length > 0) {
    const gridEl = document.getElementById("allPlacesGrid");
    if (gridEl && gridEl.children.length > 0) {
      renderAllPlaces(allPlacesCache);
    }
  }
}

function openAuthModal() {
  document.getElementById("modalAuth").classList.remove("hidden");
}

function closeAuthModal() {
  document.getElementById("modalAuth").classList.add("hidden");
}

function setAuthTab(tab) {
  const formLogin = document.getElementById("formLogin");
  const formRegister = document.getElementById("formRegister");
  const tabLogin = document.getElementById("tabLogin");
  const tabRegister = document.getElementById("tabRegister");

  if (tab === "login") {
    formLogin.classList.remove("hidden");
    formRegister.classList.add("hidden");
    tabLogin.className = "flex-1 pb-3 text-xs font-bold border-b-2 border-[#E11D48] text-[#E11D48]";
    tabRegister.className = "flex-1 pb-3 text-xs font-bold text-slate-400";
  } else {
    formLogin.classList.add("hidden");
    formRegister.classList.remove("hidden");
    tabRegister.className = "flex-1 pb-3 text-xs font-bold border-b-2 border-emerald-600 text-emerald-600";
    tabLogin.className = "flex-1 pb-3 text-xs font-bold text-slate-400";
  }
}

function fillDemoAccount(user, pass) {
  setAuthTab("login");
  document.getElementById("loginUsername").value = user;
  document.getElementById("loginPassword").value = pass;
}

async function handleLogin(e) {
  e.preventDefault();
  const u = document.getElementById("loginUsername").value.trim();
  const p = document.getElementById("loginPassword").value.trim();

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Đăng nhập thất bại");

    currentUser = data.user;
    localStorage.setItem("sggo_current_user", JSON.stringify(currentUser));
    updateAuthUI();
    closeAuthModal();
    alert(`Xin chào ${currentUser.full_name}! Bạn đã đăng nhập thành công.`);

    if (currentUser.role === "admin") {
      switchMode("admin");
    } else {
      switchMode("flow");
    }
  } catch (err) {
    alert("❌ Lỗi: " + err.message);
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const name = document.getElementById("regFullName").value.trim();
  const u = document.getElementById("regUsername").value.trim();
  const p = document.getElementById("regPassword").value.trim();

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p, full_name: name })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Đăng ký thất bại");

    currentUser = data.user;
    localStorage.setItem("sggo_current_user", JSON.stringify(currentUser));
    updateAuthUI();
    closeAuthModal();
    alert(`Đăng ký thành công! Chào mừng ${currentUser.full_name} đến với SGGo.`);
  } catch (err) {
    alert("❌ Lỗi: " + err.message);
  }
}

function handleLogout() {
  if (confirm("Bạn có chắc chắn muốn đăng xuất tài khoản?")) {
    currentUser = null;
    localStorage.removeItem("sggo_current_user");
    updateAuthUI();
    switchMode("flow");
  }
}

// ==============================================================================
// 2. TẢI DỮ LIỆU & ĐIỀU HƯỚNG TABS
// ==============================================================================

async function preloadPlaces() {
  try {
    const res = await fetch(`${API_BASE}/places`);
    allPlacesCache = await res.json();
    const countEl = document.getElementById("totalPlacesCount");
    if (countEl) countEl.innerText = allPlacesCache.length;
  } catch (e) {
    console.warn("Backend offline hoặc đang nạp CSDL.");
  }
}

function switchMode(mode) {
  const isAdmin = currentUser && currentUser.role === "admin";
  if (mode === "admin" && !isAdmin) {
    alert("⛔ Quyền truy cập bị từ chối: Khu vực này chỉ dành riêng cho Quản trị viên (Admin)!");
    openAuthModal();
    switchMode("flow");
    return;
  }

  document.getElementById("viewFlow").classList.toggle("hidden", mode !== "flow");
  document.getElementById("viewAI").classList.toggle("hidden", mode !== "ai");
  document.getElementById("viewAll").classList.toggle("hidden", mode !== "all");
  const viewAdmin = document.getElementById("viewAdmin");
  if (viewAdmin) viewAdmin.classList.toggle("hidden", mode !== "admin");

  const standardTabs = {
    flow: document.getElementById("navFlow"),
    ai: document.getElementById("navAI"),
    all: document.getElementById("navAll")
  };

  Object.keys(standardTabs).forEach(k => {
    if (standardTabs[k]) {
      standardTabs[k].className = (k === mode) ? "tab-pill active whitespace-nowrap" : "tab-pill whitespace-nowrap";
    }
  });

  const navAdmin = document.getElementById("navAdmin");
  if (navAdmin) {
    if (isAdmin) {
      navAdmin.classList.remove("hidden");
      navAdmin.style.setProperty("display", "inline-flex", "important");
      navAdmin.className = (mode === "admin")
        ? "tab-pill active text-rose-600 font-extrabold whitespace-nowrap"
        : "tab-pill text-rose-600 font-bold whitespace-nowrap";
    } else {
      navAdmin.classList.add("hidden");
      navAdmin.style.setProperty("display", "none", "important");
    }
  }

  if (mode === "all") {
    if (!exploreUserCoords && userGPSCoords) {
      setExploreLocationPreset("Vị trí GPS của bạn", userGPSCoords.lat, userGPSCoords.lon);
    } else {
      filterAllPlaces();
    }
  }
  if (mode === "admin" && isAdmin) loadAdminDashboard();
}

function parsePlaceTiers(tagsStr) {
  if (!tagsStr || typeof tagsStr !== "string") return { tier1: [], tier2: [] };
  const str = tagsStr.trim();
  if (str.includes("tier1:") || str.includes("tier2:")) {
    const parts = str.split("|");
    let t1 = [], t2 = [];
    parts.forEach(p => {
      const trimmed = p.trim();
      if (trimmed.startsWith("tier1:")) {
        t1 = trimmed.replace("tier1:", "").split(",").map(x => x.trim()).filter(Boolean);
      } else if (trimmed.startsWith("tier2:")) {
        t2 = trimmed.replace("tier2:", "").split(",").map(x => x.trim()).filter(Boolean);
      }
    });
    return { tier1: t1, tier2: t2 };
  } else {
    const all = str.split(",").map(x => x.trim()).filter(Boolean);
    return { tier1: all.slice(0, 2), tier2: all.slice(2) };
  }
}

function onAdminTagChange(tag, tier) {
  const chkT1 = document.getElementById(`chk_t1_${tag}`);
  const chkT2 = document.getElementById(`chk_t2_${tag}`);
  if (tier === 1 && chkT1 && chkT1.checked) {
    if (chkT2) chkT2.checked = false;
  } else if (tier === 2 && chkT2 && chkT2.checked) {
    if (chkT1) chkT1.checked = false;
  }
  syncAdminTagsInput();
}

function syncAdminTagsInput() {
  const allTags = ['di_1_minh', 'hen_ho', 'nhom_ban', 'gia_dinh'];
  const t1 = [];
  const t2 = [];
  allTags.forEach(t => {
    const c1 = document.getElementById(`chk_t1_${t}`);
    const c2 = document.getElementById(`chk_t2_${t}`);
    if (c1 && c1.checked) t1.push(t);
    if (c2 && c2.checked) t2.push(t);
  });
  const hiddenInp = document.getElementById("formTags");
  if (hiddenInp) {
    hiddenInp.value = `tier1:${t1.join(",")}|tier2:${t2.join(",")}`;
  }
}

function isPlaceCurrentlyOpen(openStr, closeStr) {
  if (!openStr || !closeStr) return true;
  const now = new Date();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  const [oH, oM] = openStr.split(":").map(Number);
  const [cH, cM] = closeStr.split(":").map(Number);
  const openMinutes = oH * 60 + (oM || 0);
  let closeMinutes = cH * 60 + (cM || 0);

  if (closeMinutes < openMinutes) {
    closeMinutes += 24 * 60;
  }

  return currentMinutes >= openMinutes && currentMinutes <= closeMinutes;
}

// ==============================================================================
// 3. KHÁM PHÁ NHANH & THANH TÓM TẮT LỰA CHỌN (BREADCRUMB)
// ==============================================================================

function updateSelectionSummaryUI() {
  const catEl = document.getElementById("summaryCategory");
  const ctxEl = document.getElementById("summaryContext");
  const bdgEl = document.getElementById("summaryBudget");
  if (!catEl || !ctxEl || !bdgEl) return;

  // 1. Cập nhật Mục đích
  if (userChoices.category === "an_uong") {
    catEl.innerHTML = `<span class="truncate">1. Đi Ăn Uống</span>`;
    catEl.className = "cursor-pointer py-1.5 px-2 rounded-xl border border-rose-300 bg-rose-50 text-[#E11D48] font-black shadow-xs transition flex items-center justify-center gap-1 text-center truncate";
  } else if (userChoices.category === "di_choi") {
    catEl.innerHTML = `<span class="truncate">1. Đi Vui Chơi</span>`;
    catEl.className = "cursor-pointer py-1.5 px-2 rounded-xl border border-teal-300 bg-teal-50 text-teal-800 font-black shadow-xs transition flex items-center justify-center gap-1 text-center truncate";
  } else {
    catEl.innerHTML = `<span class="truncate">1. Mục đích</span>`;
    catEl.className = "cursor-pointer py-1.5 px-2 rounded-xl border border-slate-200 bg-slate-50 text-slate-500 hover:border-[#E11D48] hover:bg-rose-50/60 transition flex items-center justify-center gap-1 text-center truncate";
  }

  // 2. Cập nhật Bối cảnh
  const ctxMap = {
    "di_1_minh": "2. Đi 1 mình",
    "nguoi_yeu": "2. Cặp đôi",
    "ban_be": "2. Nhóm bạn",
    "gia_dinh": "2. Gia đình"
  };
  if (userChoices.context && userChoices.context in ctxMap) {
    ctxEl.innerHTML = `<span class="truncate">${ctxMap[userChoices.context]}</span>`;
    ctxEl.className = "cursor-pointer py-1.5 px-2 rounded-xl border border-rose-300 bg-rose-50 text-[#E11D48] font-black shadow-xs transition flex items-center justify-center gap-1 text-center truncate";
  } else {
    ctxEl.innerHTML = `<span class="truncate">2. Đi cùng</span>`;
    ctxEl.className = "cursor-pointer py-1.5 px-2 rounded-xl border border-slate-200 bg-slate-50 text-slate-500 hover:border-[#E11D48] hover:bg-rose-50/60 transition flex items-center justify-center gap-1 text-center truncate";
  }

  // 3. Cập nhật Ngân sách
  const bdgMap = {
    "free": "3. Miễn phí (0đ)",
    "under_50k": "3. < 50k",
    "50k_100k": "3. 50k - 100k",
    "100k_250k": "3. 100k - 250k",
    "above_250k": "3. > 250k",
    "all": "3. Tùy duyên"
  };
  if (userChoices.price_level === "custom" && userChoices.custom_budget) {
    const formatted = userChoices.custom_budget >= 1000000 
      ? (userChoices.custom_budget / 1000000).toFixed(1) + 'Tr' 
      : (userChoices.custom_budget / 1000) + 'k';
    bdgEl.innerHTML = `<span class="truncate">3. ${formatted}</span>`;
    bdgEl.className = "cursor-pointer py-1.5 px-2 rounded-xl border border-rose-300 bg-rose-50 text-[#E11D48] font-black shadow-xs transition flex items-center justify-center gap-1 text-center truncate";
  } else if (userChoices.price_level && userChoices.price_level in bdgMap) {
    bdgEl.innerHTML = `<span class="truncate">${bdgMap[userChoices.price_level]}</span>`;
    bdgEl.className = "cursor-pointer py-1.5 px-2 rounded-xl border border-rose-300 bg-rose-50 text-[#E11D48] font-black shadow-xs transition flex items-center justify-center gap-1 text-center truncate";
  } else {
    bdgEl.innerHTML = `<span class="truncate">3. Ngân sách</span>`;
    bdgEl.className = "cursor-pointer py-1.5 px-2 rounded-xl border border-slate-200 bg-slate-50 text-slate-500 hover:border-[#E11D48] hover:bg-rose-50/60 transition flex items-center justify-center gap-1 text-center truncate";
  }
}

function selectAnswer(key, value, nextStep) {
  userChoices[key] = value;
  currentFlowOffset = 0;
  if (key === "price_level") {
    userChoices.custom_budget = null;
  }
  updateSelectionSummaryUI();

  if (nextStep === "finish") {
    showFinishResults(0);
  } else {
    document.querySelectorAll(".step-card").forEach(el => el.classList.add("hidden"));
    document.getElementById(`step${nextStep}`).classList.remove("hidden");
  }
}

function handleCustomBudgetSubmit() {
  const input = document.getElementById("customBudgetInput");
  const val = parseInt(input.value);
  if (!val || val <= 0) {
    alert("Vui lòng nhập một số tiền hợp lệ (ví dụ: 75000)!");
    return;
  }
  userChoices.price_level = "custom";
  userChoices.custom_budget = val;
  currentFlowOffset = 0;
  updateSelectionSummaryUI();
  showFinishResults(0);
}


function goBackStep(step) {
  document.querySelectorAll(".step-card").forEach(el => el.classList.add("hidden"));
  document.getElementById(`step${step}`).classList.remove("hidden");
}

function restartFlow() {
  userChoices = { category: null, context: null, price_level: null, custom_budget: null };
  currentFlowOffset = 0;
  const customInp = document.getElementById("customBudgetInput");
  if (customInp) customInp.value = "";
  updateSelectionSummaryUI();
  document.querySelectorAll(".step-card").forEach(el => el.classList.add("hidden"));
  document.getElementById("step1").classList.remove("hidden");
}

async function showFinishResults(offset = 0) {
  currentFlowOffset = Math.max(0, offset);
  document.querySelectorAll(".step-card").forEach(el => el.classList.add("hidden"));
  const finishContainer = document.getElementById("stepFinish");
  finishContainer.classList.remove("hidden");

  // Cập nhật trạng thái nút Quay lại 3 quán trước
  const btnPrev = document.getElementById("btnPrevFlow");
  if (btnPrev) {
    btnPrev.disabled = (currentFlowOffset <= 0);
  }

  // Cập nhật badge tóm tắt tiêu chí khoa học
  const criteriaBadge = document.getElementById("finishCriteriaBadge");
  if (criteriaBadge) {
    const catText = userChoices.category === "an_uong" ? "🍜 Ăn uống" : (userChoices.category === "di_choi" ? "📸 Vui chơi" : "Mục đích");
    const ctxMap = { "di_1_minh": "🎧 Đi 1 mình", "nguoi_yeu": "💑 Cặp đôi", "ban_be": "🎉 Bạn bè", "gia_dinh": "👨‍👩‍👧 Gia đình" };
    const bdgMap = { "under_50k": "< 50k", "50k_100k": "50k-100k", "100k_250k": "100k-250k", "above_250k": "> 250k" };
    const ctxText = ctxMap[userChoices.context] || "Đồng hành";
    let bdgText = bdgMap[userChoices.price_level] || "Ngân sách";
    if (userChoices.price_level === "custom" && userChoices.custom_budget) {
      bdgText = `${userChoices.custom_budget.toLocaleString()}đ`;
    }
    criteriaBadge.innerHTML = `<span class="bg-rose-100 text-[#E11D48] px-2.5 py-0.5 rounded-md font-extrabold text-[10px]">🎯 TIÊU CHÍ: ${catText} • ${ctxText} • 💰 ${bdgText}</span>`;
  }

  const resultsBox = document.getElementById("flowResults");
  resultsBox.innerHTML = `<div class="p-8 text-center text-xs text-slate-500 font-bold"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Đang phân tích ma trận dữ liệu và chọn lọc quán phù hợp...</div>`;

  try {
    const payload = { ...userChoices, offset: currentFlowOffset };
    const res = await fetch(`${API_BASE}/quick-recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const places = await res.json();

    const fallbackEl = document.getElementById("flowFallbackNotice");
    if (fallbackEl) {
      const fallbackItem = places.find(p => p.free_fallback_notice);
      if (fallbackItem && fallbackItem.free_fallback_notice) {
        fallbackEl.innerHTML = `<i class="fa-solid fa-circle-info text-amber-600 mr-2 text-sm flex-shrink-0"></i><span>${fallbackItem.free_fallback_notice}</span>`;
        fallbackEl.classList.remove("hidden");
      } else {
        fallbackEl.classList.add("hidden");
      }
    }

    renderFinishCards(places);
  } catch (e) {
    resultsBox.innerHTML = `<div class="p-4 bg-red-50 text-red-600 rounded-xl text-xs">Chưa thể kết nối CSDL Backend.</div>`;
  }
}

function prevFlowResults() {
  if (currentFlowOffset >= 3) {
    currentFlowOffset -= 3;
    showFinishResults(currentFlowOffset);
    document.getElementById("stepFinish")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function rotateFlowResults() {
  currentFlowOffset += 3;
  showFinishResults(currentFlowOffset);
  document.getElementById("stepFinish")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

// HÀM HIỂN THỊ ẢNH CHÂN THỰC: 1 LÀ ẢNH THẬT, 2 LÀ HIỂN THỊ "CHƯA CÓ ẢNH" (KHÔNG DÙNG ẢNH ẢO)
function renderPlaceImage(p, widthClass = "w-full", heightClass = "h-full", customClass = "") {
  const imgSrc = p.image_url;
  if (imgSrc && imgSrc.trim()) {
    return `
      <img src="${imgSrc}" onerror="this.outerHTML='<div class=\'${widthClass} ${heightClass} bg-slate-100 rounded-2xl flex flex-col items-center justify-center text-slate-400 border border-slate-200 select-none\'><i class=\'fa-solid fa-camera text-slate-300 text-xl mb-1\'></i><span class=\'text-[11px] font-bold text-slate-400\'>Chưa có ảnh</span></div>';" class="${widthClass} ${heightClass} object-cover rounded-2xl shadow-inner ${customClass}" alt="${p.name}" />
    `;
  }
  return `
    <div class="${widthClass} ${heightClass} bg-slate-100 border border-slate-200 rounded-2xl flex flex-col items-center justify-center text-slate-400 select-none ${customClass}">
      <i class="fa-solid fa-camera text-slate-300 text-2xl mb-1"></i>
      <span class="text-[11px] font-bold text-slate-400">Chưa có ảnh</span>
    </div>
  `;
}

// ==============================================================================
// TAB 1: THẺ GỢI Ý KẾT QUẢ 2 CỘT RỘNG RÃI (DÀNH RIÊNG CHO TAB KHÁM PHÁ NHANH)
// CỰC KỲ NHẤN MẠNH: TÊN QUÁN, SỐ SAO (NGAY DƯỚI TÊN), GIÁ TIỀN, MỞ CỬA, 2 COMMENT
// ==============================================================================
function buildRecommendCardHTML(p, idx) {
  const isEat = p.category === "an_uong";
  const hasHours = Boolean(p.hours_display || (p.open_time && p.close_time));
  const isOpen = isPlaceCurrentlyOpen(p.open_time, p.close_time);
  const gmapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.name + ' ' + p.address)}`;

  const isFree = (p.min_price === 0 && p.max_price === 0);
  const cleanPrice = p.price_display ? p.price_display.replace(/Khoảng\s*/gi, "").replace(/\(.*?\)/g, "").trim() : null;
  const priceRangeFormatted = cleanPrice
    ? cleanPrice
    : (isFree
      ? "Miễn phí vé vào cổng"
      : `${p.min_price ? p.min_price.toLocaleString() + 'đ' : ''} – ${p.max_price ? p.max_price.toLocaleString() + 'đ' : ''}`);

  // Làm sạch và định dạng Giờ cao điểm (Nhấn mạnh nổi bật đồng điệu với Mức giá)
  const rawPeak = (p.peak_hours && p.peak_hours !== 'Chưa rõ') ? p.peak_hours : '';
  const cleanPeakHours = rawPeak.replace(/\s*\([^\)]*đông[^\)]*\)/gi, '').trim();
  const hasPeak = Boolean(cleanPeakHours && cleanPeakHours !== 'Chưa rõ');
  const cleanPeakHoursText = hasPeak ? cleanPeakHours : 'Chưa rõ (quán chưa cập nhật)';
  const peakHoursFontSize = !hasPeak 
    ? 'text-xs font-semibold text-amber-800/80 italic' 
    : (cleanPeakHours.length > 20 ? 'text-base sm:text-lg' : 'text-xl sm:text-2xl');

  // Khoảng cách: CHỈ HIỂN THỊ KHI NGƯỜI DÙNG CÓ BẬT ĐỊNH VỊ GPS
  let distanceHTML = "";
  if (typeof p.distanceKm === "number" && !isNaN(p.distanceKm) && exploreUserCoords) {
    const isWalk = p.distanceKm <= 0.6;
    const walkTime = Math.max(1, Math.round(p.distanceKm * 12));
    const bikeTime = Math.max(1, Math.round(p.distanceKm * 2.5));
    const distStr = p.distanceKm < 1 ? `${Math.round(p.distanceKm * 1000)}m` : `${p.distanceKm.toFixed(1)} km`;

    distanceHTML = `
      <span class="ml-2 px-2.5 py-0.5 rounded-full text-[11px] font-extrabold ${isWalk ? 'bg-emerald-100 text-emerald-900 border border-emerald-300' : 'bg-blue-100 text-blue-900 border border-blue-300'} whitespace-nowrap inline-flex items-center gap-1">
        <i class="fa-solid ${isWalk ? 'fa-person-walking' : 'fa-motorcycle'} text-[11px]"></i>
        <span>Cách bạn ${distStr}</span>
        <span class="font-normal opacity-85">(${isWalk ? `~${walkTime}p đi bộ` : `~${bikeTime}p xe máy`})</span>
      </span>
    `;
  }

  const imageHtml = renderPlaceImage(p, "w-full", "h-full");

  return `
    <div class="recommend-card-2col">
      <div class="grid grid-cols-1 md:grid-cols-12 gap-6 md:gap-7 items-stretch">
        
        <!-- ==================== CỘT TRÁI (45% - FACTS & THÔNG TIN CỐT LÕI) ==================== -->
        <div class="md:col-span-5 flex flex-col justify-between">
          <div>
            <!-- Ảnh Quán Lớn + Badge Thứ Hạng + Trạng Thái Mở Cửa Nhấn Mạnh Ngay Trên Ảnh -->
            <div onclick="openPlaceDetailById(${p.id})" class="relative w-full h-52 sm:h-56 rounded-2xl overflow-hidden mb-3.5 border border-slate-200/90 shadow-xs cursor-pointer group">
              ${imageHtml}
              <!-- Container 2 Badge Tránh Đè Lẫn Nhau -->
              <div class="absolute top-3 left-3 right-3 flex items-center justify-between gap-2 pointer-events-none">
                <!-- Badge Thứ hạng -->
                <span class="text-xs font-black uppercase text-white bg-[#E11D48] px-3 py-1 rounded-xl shadow-md shrink-0">
                  GỢI Ý #${idx + 1}
                </span>
                <!-- TRẠNG THÁI MỞ CỬA: RÚT GỌN TINH TẾ, KHÔNG TRÀN LẤN -->
                ${hasHours ? (isOpen ? `
                  <span class="bg-emerald-600/95 backdrop-blur-xs text-white text-[11px] font-black px-2.5 py-1 rounded-full shadow-md flex items-center gap-1.5 uppercase tracking-wide shrink-0">
                    <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                    <span>Đang mở cửa</span>
                  </span>
                ` : `
                  <span class="bg-rose-600/95 backdrop-blur-xs text-white text-[11px] font-black px-2.5 py-1 rounded-full shadow-md flex items-center gap-1.5 uppercase tracking-wide shrink-0">
                    <span class="w-2 h-2 rounded-full bg-white"></span>
                    <span>Đã đóng cửa</span>
                  </span>
                `) : ''}
              </div>
            </div>

            <!-- Thể loại & Quận & Tag đề cử (Gom thành 1 hàng ngang tinh tế) -->
            <div class="flex items-center gap-2 flex-wrap mb-2.5">
              <span class="text-[11px] font-black uppercase text-[#E11D48] bg-[#FFE4E6] px-2.5 py-0.5 rounded-lg tracking-wider">
                ${isEat ? 'Ẩm Thực Sài Gòn' : 'Điểm Đến & Vui Chơi'}
              </span>
              ${p.district ? `
                <span class="text-[11px] font-bold text-slate-600 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-lg flex items-center gap-1">
                  <i class="fa-solid fa-location-dot text-[#E11D48] text-[10px]"></i>
                  <span>${p.district}</span>
                </span>
              ` : ''}
              ${distanceHTML}
              ${p.is_admin_choice === 1 ? '<span class="text-[10px] bg-amber-100 text-amber-900 font-extrabold px-2 py-0.5 rounded-md border border-amber-300 flex items-center gap-1"><i class="fa-solid fa-crown text-amber-600"></i> Quán Đề Cử</span>' : ''}
            </div>

            <!-- Tên quán (Headline lớn, đậm nét) -->
            <h3 onclick="openPlaceDetailById(${p.id})" class="font-black text-slate-900 text-xl sm:text-2xl tracking-tight leading-snug mb-2 hover:text-[#E11D48] transition cursor-pointer" title="Bấm để xem chi tiết quán">
              ${p.name}
            </h3>

            <!-- SỐ SAO & ĐÁNH GIÁ (GỌN GÀNG, KHÔNG BAO GIỜ BỊ TRÀN HÀNG) -->
            <div class="flex items-center gap-2.5 mb-4 flex-nowrap">
              <div class="rating-pill-prominent shadow-2xs shrink-0">
                <i class="fa-solid fa-star text-amber-500 text-sm"></i>
                <span class="text-base font-black text-amber-950">${p.rating}</span>
                <span class="text-xs text-amber-700 font-extrabold">/ 5.0</span>
              </div>
              <span class="text-xs font-bold text-slate-500 truncate">(${parseInt(p.reviews_count || 100).toLocaleString()} đánh giá)</span>
            </div>
          </div>

          <!-- MỨC GIÁ: CỰC KỲ NHẤN MẠNH RIÊNG BIỆT Ở ĐÁY CỘT TRÁI -->
          <div class="price-block-prominent">
            <div class="flex items-center justify-between w-full mb-1">
              <span class="text-[11px] font-black uppercase text-slate-500 tracking-wider flex items-center gap-1.5 whitespace-nowrap">
                <i class="fa-solid fa-wallet text-[#E11D48] text-xs flex-shrink-0"></i>
                <span class="whitespace-nowrap">Mức giá tham khảo</span>
              </span>
            </div>
            <div class="flex items-baseline gap-1.5 whitespace-nowrap">
              <span class="text-xl sm:text-2xl font-black text-emerald-800 tracking-tight whitespace-nowrap">
                ${priceRangeFormatted}
              </span>
            </div>
          </div>
        </div>

        <!-- ==================== CỘT PHẢI (55% - EXPERIENCE, 2 REVIEWS & ACTIONS) ==================== -->
        <div class="md:col-span-7 flex flex-col justify-between pl-0 md:pl-6 md:border-l md:border-slate-200/90 pt-5 md:pt-0 border-t md:border-t-0 border-slate-200/90">
          <div>
            <!-- Giờ Cao Điểm: Nhấn mạnh nổi bật tương tự Mức giá -->
            <div class="peak-hours-prominent mb-4">
              <div class="flex items-center justify-between w-full mb-1">
                <span class="text-[11px] font-black uppercase text-amber-800 tracking-wider flex items-center gap-1.5 whitespace-nowrap">
                  <i class="fa-solid fa-clock-rotate-left text-amber-600 text-xs flex-shrink-0"></i>
                  <span>Giờ cao điểm</span>
                </span>
              </div>
              <div class="flex items-baseline gap-1.5">
                <span class="${peakHoursFontSize} font-black text-amber-950 tracking-tight leading-tight">
                  ${cleanPeakHoursText}
                </span>
              </div>
            </div>

            <!-- 2 KHỐI COMMENT KHEN & CHÊ: CỰC KỲ NHẤN MẠNH DẠNG REVIEW CARDS -->
            <div class="space-y-3 mb-5">
              <!-- Khối Khen 5 sao -->
              <div class="review-card-khen shadow-2xs">
                <div class="flex items-center justify-between mb-1.5">
                  <span class="font-black text-emerald-950 uppercase text-xs tracking-wider flex items-center gap-1.5">
                    <i class="fa-solid fa-thumbs-up text-emerald-600 text-sm"></i>
                    <span>Đánh giá khen ngợi (5 sao):</span>
                  </span>
                </div>
                <p class="font-medium italic text-emerald-950 text-[13px] leading-relaxed">
                  ${p.best_review ? `"${p.best_review}"` : '<span class="text-slate-400 not-italic">Chưa có nhận xét khen</span>'}
                </p>
              </div>

              <!-- Khối Lưu ý / Góp ý -->
              <div class="review-card-luuy shadow-2xs">
                <div class="flex items-center justify-between mb-1.5">
                  <span class="font-black text-rose-950 uppercase text-xs tracking-wider flex items-center gap-1.5">
                    <i class="fa-solid fa-triangle-exclamation text-[#E11D48] text-sm"></i>
                    <span>Lưu ý trải nghiệm & Góp ý:</span>
                  </span>
                </div>
                <p class="font-medium italic text-slate-800 text-[13px] leading-relaxed">
                  ${p.worst_review ? `"${p.worst_review}"` : '<span class="text-slate-400 not-italic">Chưa có lưu ý đặc biệt</span>'}
                </p>
              </div>
            </div>
          </div>

          <!-- Hàng Nút Hành Động (Đáy cột phải) -->
          <div class="pt-4 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2.5">
            <!-- Cụm trái: Chi tiết quán -->
            <div class="flex items-center gap-2">
              <button onclick="openPlaceDetailById(${p.id})" title="Xem đầy đủ thông tin" class="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer shadow-xs">
                <i class="fa-solid fa-circle-info text-slate-600"></i>
                <span>Chi tiết quán</span>
              </button>
            </div>

            <!-- Cụm phải: Nút Sửa quán (Admin) đặt ngay sát bên cạnh Nút Google Maps -->
            <div class="flex items-center gap-2">
              ${(currentUser && currentUser.role === 'admin') ? `
                <button onclick="openEditPlaceModalById(${p.id})" title="Sửa dữ liệu quán" class="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer shadow-sm whitespace-nowrap">
                  <i class="fa-solid fa-pen-to-square"></i>
                  <span>Sửa quán</span>
                </button>
              ` : ''}
              <a href="${gmapsUrl}" target="_blank" title="Mở trang Google Maps chính thức của quán" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-black transition flex items-center gap-2 shadow-sm whitespace-nowrap">
                <i class="fa-brands fa-google text-sm"></i>
                <span>Google Maps</span>
                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
              </a>
            </div>
          </div>
        </div>

      </div>
    </div>
  `;
}

// Render 3 quán kết quả bước Finish (Sử dụng Thẻ Gợi Ý 2 Cột Cực Kỳ Nhấn Mạnh)
function renderFinishCards(places) {
  const resultsBox = document.getElementById("flowResults");
  resultsBox.innerHTML = "";

  if (!places || places.length === 0) {
    resultsBox.innerHTML = `<div class="p-8 text-center text-xs text-slate-500 bg-white rounded-2xl border border-slate-200">Không tìm thấy địa điểm phù hợp, vui lòng thử lại tiêu chí khác.</div>`;
    return;
  }

  places.forEach((p, idx) => {
    resultsBox.innerHTML += buildRecommendCardHTML(p, currentFlowOffset + idx);
  });
}

// ==============================================================================
// 4. LẬP LỘ TRÌNH AI (ĐỊNH TUYẾN THÔNG MINH GPS & GEMINI AI)
// ==============================================================================

let userGPSCoords = null;
let leafletMap = null;
let leafletMarkersGroup = null;

function getCurrentGPSLocation() {
  const btn = document.getElementById("btnGetGPS");
  const input = document.getElementById("aiStartLoc");
  const icon = document.getElementById("gpsStatusIcon");

  if (!navigator.geolocation) {
    alert("Trình duyệt của bạn không hỗ trợ định vị GPS Geolocation.");
    return;
  }

  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang lấy GPS...</span>`;
  btn.disabled = true;

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      userGPSCoords = {
        lat: pos.coords.latitude,
        lon: pos.coords.longitude
      };
      // Đồng bộ sang Tab Tự chọn nếu bên đó chưa có tọa độ
      if (!exploreUserCoords) {
        exploreUserCoords = { ...userGPSCoords };
        const expInput = document.getElementById("exploreLocationInput");
        if (expInput) expInput.value = `Vị trí GPS hiện tại (${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)})`;
        const expBadge = document.getElementById("exploreGpsStatusBadge");
        if (expBadge) expBadge.classList.remove("hidden");
        const expClear = document.getElementById("btnClearExploreLoc");
        if (expClear) expClear.classList.remove("hidden");
      }
      input.value = `Vị trí GPS hiện tại (${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)})`;
      if (icon) icon.classList.remove("hidden");
      btn.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-600"></i> <span class="text-emerald-700">Đã nhận GPS</span>`;
      btn.disabled = false;
    },
    (err) => {
      alert("Không thể lấy vị trí GPS: " + err.message + ". Bạn có thể nhập địa chỉ hoặc bấm vào các nút gợi ý có sẵn.");
      btn.innerHTML = `<i class="fa-solid fa-location-crosshairs"></i> <span>Dùng GPS hiện tại</span>`;
      btn.disabled = false;
    },
    { timeout: 8000, enableHighAccuracy: true }
  );
}

function setStartLocation(loc) {
  document.getElementById("aiStartLoc").value = loc;
  userGPSCoords = null;
  const icon = document.getElementById("gpsStatusIcon");
  if (icon) icon.classList.add("hidden");
  const btn = document.getElementById("btnGetGPS");
  if (btn) btn.innerHTML = `<i class="fa-solid fa-location-crosshairs"></i> <span>Dùng GPS hiện tại</span>`;
}

function setFreeTimePreset(timeStr) {
  document.getElementById("aiTime").value = timeStr;
}

function selectAICompanion(val) {
  aiCompanion = val;
  const map = {
    di_1_minh: "comp_di_1_minh",
    nguoi_yeu: "comp_nguoi_yeu",
    ban_be: "comp_ban_be",
    gia_dinh: "comp_gia_dinh"
  };
  Object.keys(map).forEach(k => {
    const btn = document.getElementById(map[k]);
    if (!btn) return;
    if (k === val) {
      btn.className = "companion-chip active py-2.5 px-3 rounded-xl border-2 border-[#E11D48] bg-rose-50 font-bold text-[#E11D48] shadow-xs transition flex items-center justify-center gap-1.5 cursor-pointer text-center";
    } else {
      btn.className = "companion-chip py-2.5 px-3 rounded-xl border border-slate-200 bg-white font-bold text-slate-600 hover:border-slate-300 transition flex items-center justify-center gap-1.5 cursor-pointer text-center";
    }
  });
}

function selectAIPurpose(val) {
  aiPurpose = val;
  const map = {
    an_uong: "purp_an_uong",
    di_choi: "purp_di_choi",
    ca_hai: "purp_ca_hai"
  };
  Object.keys(map).forEach(k => {
    const btn = document.getElementById(map[k]);
    if (!btn) return;
    if (k === val) {
      btn.className = "purpose-chip active py-2.5 px-3 rounded-xl border-2 border-[#E11D48] bg-rose-50 font-bold text-[#E11D48] shadow-xs transition flex items-center justify-center gap-1.5 cursor-pointer text-center";
    } else {
      btn.className = "purpose-chip py-2.5 px-3 rounded-xl border border-slate-200 bg-white font-bold text-slate-600 hover:border-slate-300 transition flex items-center justify-center gap-1.5 cursor-pointer text-center";
    }
  });
}

function appendTakeNote(text) {
  const input = document.getElementById("aiTakeNote");
  if (!input) return;
  if (!input.value.trim()) {
    input.value = text;
  } else if (!input.value.includes(text)) {
    input.value = `${input.value.trim()}, ${text}`;
  }
}

function setContextPreset(ctxStr) {
  appendTakeNote(ctxStr);
}

function toggleItineraryMap() {
  const wrapper = document.getElementById("itineraryMapWrapper");
  const btn = document.getElementById("btnToggleMap");
  if (!wrapper) return;
  
  if (wrapper.classList.contains("hidden")) {
    wrapper.classList.remove("hidden");
    if (btn) btn.innerHTML = `<i class="fa-solid fa-chevron-up"></i> <span>Thu gọn bản đồ</span>`;
    setTimeout(() => {
      if (leafletMap) leafletMap.invalidateSize();
    }, 200);
  } else {
    wrapper.classList.add("hidden");
    if (btn) btn.innerHTML = `<i class="fa-solid fa-map"></i> <span>Hiện bản đồ</span>`;
  }
}

// Cấu hình các lớp bản đồ tương tác (Google Maps, OpenStreetMap, Vệ tinh) - Hoàn toàn không bị lỗi 'API key required'
function initLeafletTileLayers(mapInstance) {
  // 1. Google Maps Đường Phố (Mặc định: cực nét, 100% tiếng Việt chuẩn Sài Gòn, tốc độ cao, không cần API key)
  const googleStreets = L.tileLayer("https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", {
    maxZoom: 20,
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    attribution: '&copy; <a href="https://maps.google.com" target="_blank" rel="noopener noreferrer">Google Maps</a>'
  });

  // 2. OpenStreetMap Chuẩn (Nguồn mở quốc tế)
  const osmStandard = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    subdomains: "abc",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>'
  });

  // 3. Google Maps Vệ Tinh Lai (Hybrid Satellite kèm tên đường)
  const googleHybrid = L.tileLayer("https://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {
    maxZoom: 20,
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    attribution: '&copy; Google Satellite'
  });

  // Mặc định nạp lớp bản đồ Google Maps vào bản đồ
  googleStreets.addTo(mapInstance);

  const baseLayers = {
    "🗺️ Đường phố (Google)": googleStreets,
    "🌐 OpenStreetMap": osmStandard,
    "🛰️ Ảnh vệ tinh": googleHybrid
  };

  // Tùy chọn: Nếu người dùng đã đăng ký key miễn phí tại carto.com/basemaps/apikey
  const cartoApiKey = window.CARTO_API_KEY || localStorage.getItem("CARTO_API_KEY");
  if (cartoApiKey) {
    const cartoLayer = L.tileLayer(`https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${cartoApiKey}`, {
      attribution: '&copy; CARTO',
      subdomains: "abcd",
      maxZoom: 20
    });
    baseLayers["🏙️ CartoDB Voyager"] = cartoLayer;
  }

  try {
    L.control.layers(baseLayers, null, { position: "topright", collapsed: true }).addTo(mapInstance);
  } catch (e) {
    console.warn("Không thể khởi tạo bộ chọn lớp bản đồ:", e);
  }

  return googleStreets;
}

// Hàm hỗ trợ thiết lập hoặc xóa Carto API key tùy chọn
window.setCartoApiKey = function(key) {
  if (key && key.trim()) {
    localStorage.setItem("CARTO_API_KEY", key.trim());
    alert("✅ Đã lưu CARTO API Key thành công! Vui lòng tải lại trang (F5) để hiển thị thêm lớp CartoDB.");
  } else {
    localStorage.removeItem("CARTO_API_KEY");
    alert("🗑️ Đã xóa CARTO API Key! Bản đồ tiếp tục dùng Google Maps mặc định.");
  }
};

function renderItineraryMap(startCoords, steps) {
  const mapContainer = document.getElementById("itineraryMap");
  if (!mapContainer || typeof L === "undefined") return;

  if (!leafletMap) {
    leafletMap = L.map("itineraryMap", {
      zoomControl: true,
      scrollWheelZoom: false
    });
    initLeafletTileLayers(leafletMap);
    leafletMarkersGroup = L.featureGroup().addTo(leafletMap);
  } else {
    leafletMarkersGroup.clearLayers();
  }

  const points = [];

  // 1. Marker Điểm xuất phát
  if (startCoords && startCoords.lat && startCoords.lon) {
    const startLatLng = [startCoords.lat, startCoords.lon];
    points.push(startLatLng);

    const startIcon = L.divIcon({
      className: "custom-leaflet-marker",
      html: `<div style="background-color: #10B981; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 2.5px solid white;"><i class="fa-solid fa-location-dot"></i></div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 32],
      popupAnchor: [0, -32]
    });

    L.marker(startLatLng, { icon: startIcon })
      .bindPopup(`<strong>Điểm xuất phát</strong><br>${document.getElementById("aiStartLoc").value}`)
      .addTo(leafletMarkersGroup);
  }

  // 2. Markers cho 3 trạm
  const colors = ["#E11D48", "#2563EB", "#059669"];
  steps.forEach((s, idx) => {
    if (s.lat && s.lon) {
      const latLng = [s.lat, s.lon];
      points.push(latLng);

      const stepIcon = L.divIcon({
        className: "custom-leaflet-marker",
        html: `<div style="background-color: ${colors[idx] || '#E11D48'}; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 2.5px solid white;">${idx + 1}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
      });

      const popupHtml = `
        <div style="min-width: 170px; font-family: sans-serif; line-height: 1.4;">
          <div style="font-weight: 800; font-size: 12px; color: #0F172A;">Trạm ${idx + 1}: ${s.action}</div>
          <div style="font-weight: 700; color: #E11D48; margin-top: 3px;">${s.location}</div>
          <div style="font-size: 11px; color: #64748B; margin-top: 2px;">🕒 ${s.time}</div>
          ${s.must_try_tip ? `<div style="font-size: 11px; color: #047857; margin-top: 3px; font-weight: 600;">💡 ${s.must_try_tip}</div>` : ''}
        </div>
      `;

      L.marker(latLng, { icon: stepIcon })
        .bindPopup(popupHtml)
        .addTo(leafletMarkersGroup);
    }
  });

  // 3. Vẽ polyline nối các trạm
  if (points.length >= 2) {
    L.polyline(points, {
      color: "#2563EB",
      weight: 4,
      opacity: 0.85,
      dashArray: "6, 8"
    }).addTo(leafletMarkersGroup);
    leafletMap.fitBounds(leafletMarkersGroup.getBounds(), { padding: [40, 40] });
  }

  setTimeout(() => {
    if (leafletMap) leafletMap.invalidateSize();
  }, 350);
}

// ==============================================================================
// 4.1 QUẢN LÝ NGÂN SÁCH & RÀNG BUỘC TAB 3 (G6-FR03, G6-FR05, G6-FR06)
// ==============================================================================

let aiBudgetLevel = "100k_250k";
let aiTargetBudget = 250000;
let aiShuffleSeed = 0;

function selectAIBudget(level, amount) {
  aiBudgetLevel = level;
  aiTargetBudget = amount;

  ["free", "under_100k", "100k_250k", "above_250k"].forEach(l => {
    const btn = document.getElementById(`aibudget_${l}`);
    if (btn) {
      if (l === level) {
        btn.className = "companion-chip active py-2 px-3 rounded-xl border-2 border-[#E11D48] bg-rose-50 font-bold text-[#E11D48] shadow-xs transition text-center cursor-pointer";
      } else {
        btn.className = "companion-chip py-2 px-3 rounded-xl border border-slate-200 bg-white font-bold text-slate-600 hover:border-slate-300 transition text-center cursor-pointer";
      }
    }
  });

  const customInput = document.getElementById("aiCustomBudget");
  if (customInput) customInput.value = "";

  const displayEl = document.getElementById("aiBudgetValueDisplay");
  if (displayEl) {
    if (level === "free") displayEl.innerText = "0đ (Miễn phí hoàn toàn)";
    else if (level === "under_100k") displayEl.innerText = "Dưới 100.000đ / người";
    else if (level === "100k_250k") displayEl.innerText = "100.000đ – 250.000đ / người";
    else if (level === "above_250k") displayEl.innerText = "Trên 250.000đ / người";
  }
}

function onCustomAIBudgetInput() {
  const customInput = document.getElementById("aiCustomBudget");
  if (!customInput) return;
  const val = parseInt(customInput.value.replace(/\D/g, ""), 10);
  if (!isNaN(val) && val > 0) {
    aiTargetBudget = val;
    aiBudgetLevel = "custom";
    ["free", "under_100k", "100k_250k", "above_250k"].forEach(l => {
      const btn = document.getElementById(`aibudget_${l}`);
      if (btn) {
        btn.className = "companion-chip py-2 px-3 rounded-xl border border-slate-200 bg-white font-bold text-slate-600 hover:border-slate-300 transition text-center cursor-pointer";
      }
    });
    const displayEl = document.getElementById("aiBudgetValueDisplay");
    if (displayEl) displayEl.innerText = `${val.toLocaleString()}đ / người (Tự nhập)`;
  }
}

async function requestAIItinerary(isShuffle = false) {
  if (!isShuffle) {
    aiShuffleSeed = 0;
  }
  const btn = document.getElementById("btnSubmitAI");
  const resultArea = document.getElementById("aiResultArea");
  const constraintAlert = document.getElementById("aiConstraintAlert");
  const container = document.getElementById("aiTimeline");
  const summary = document.getElementById("aiSummary");
  const btnGmaps = document.getElementById("btnGmapsMultiRoute");

  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Đang tính toán & tối ưu lịch trình...`;
  btn.disabled = true;

  const startLoc = document.getElementById("aiStartLoc")?.value.trim();
  if (!startLoc && !userGPSCoords) {
    alert("📍 Vui lòng nhập điểm xuất phát hoặc bấm 'Dùng GPS hiện tại'!");
    document.getElementById("aiStartLoc")?.focus();
    btn.innerHTML = `<i class="fa-solid fa-route"></i> <span>Tạo Lịch Trình Khám Phá</span>`;
    btn.disabled = false;
    return;
  }

  const selectedModel = document.getElementById("aiModelSelect")?.value || "gemini-3.8-flash";
  const takeNoteEl = document.getElementById("aiTakeNote");
  const takeNoteVal = takeNoteEl ? takeNoteEl.value.trim() : "";

  const payload = {
    start_location: document.getElementById("aiStartLoc").value,
    start_lat: userGPSCoords ? userGPSCoords.lat : null,
    start_lon: userGPSCoords ? userGPSCoords.lon : null,
    free_time: document.getElementById("aiTime").value,
    companion: aiCompanion,
    purpose: aiPurpose,
    takenote: takeNoteVal,
    context: takeNoteVal,
    budget: aiBudgetLevel,
    budget_level: aiBudgetLevel,
    target_budget: aiTargetBudget,
    shuffle_seed: aiShuffleSeed,
    ai_model: selectedModel
  };

  try {
    const res = await fetch(`${API_BASE}/ai-itinerary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Không thể lập lộ trình");

    // XỬ LÝ VI PHẠM RÀNG BUỘC (BUSINESS RULE 3 & KIỂM THỬ BẮT BUỘC)
    if (result.feasible === false) {
      if (resultArea) resultArea.classList.add("hidden");
      if (constraintAlert) {
        constraintAlert.classList.remove("hidden");
        document.getElementById("aiConstraintTitle").innerText = result.error_code === "TIME_TOO_SHORT" ? "Thời gian rảnh quá ngắn" : "Ngân sách không đủ cho lộ trình";
        document.getElementById("aiConstraintMessage").innerText = result.message;
        document.getElementById("aiConstraintSuggestionText").innerText = result.suggestion;
        window._currentRelaxAction = {
          time: result.recommended_time || "14:00 - 18:30",
          budget: result.recommended_budget || 250000
        };
        constraintAlert.scrollIntoView({ behavior: "smooth" });
      }
      return;
    }

    // NẾU THỎA MÃN RÀNG BUỘC
    if (constraintAlert) constraintAlert.classList.add("hidden");
    if (resultArea) resultArea.classList.remove("hidden");

    // Cập nhật KPI thẻ ngân sách & thời gian (G6-FR05 MUST)
    if (result.kpi) {
      const kpi = result.kpi;
      const budgetEl = document.getElementById("aiKpiBudget");
      const budgetBadge = document.getElementById("aiKpiBudgetBadge");
      if (budgetEl) budgetEl.innerText = `${kpi.total_min_cost.toLocaleString()}đ – ${kpi.total_max_cost.toLocaleString()}đ`;
      if (budgetBadge) {
        if (kpi.is_within_budget) {
          budgetBadge.className = "inline-flex items-center gap-1 text-[10px] font-extrabold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-md mt-1";
          budgetBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span>Nằm trong ngân sách dự kiến</span>`;
        } else {
          budgetBadge.className = "inline-flex items-center gap-1 text-[10px] font-extrabold text-amber-700 bg-amber-100/80 px-2 py-0.5 rounded-md mt-1";
          budgetBadge.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> <span>Hơi vượt ngân sách</span>`;
        }
      }

      const durEl = document.getElementById("aiKpiDuration");
      const durBadge = document.getElementById("aiKpiDurationBadge");
      const h = Math.floor(kpi.total_duration_minutes / 60);
      const m = kpi.total_duration_minutes % 60;
      if (durEl) durEl.innerText = `${h > 0 ? h + ' giờ ' : ''}${m} phút (~${kpi.total_duration_minutes} phút)`;
      if (durBadge) {
        if (kpi.is_within_time) {
          durBadge.className = "inline-flex items-center gap-1 text-[10px] font-extrabold text-sky-700 bg-sky-100/80 px-2 py-0.5 rounded-md mt-1";
          durBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span>Vừa vặn khung giờ rảnh</span>`;
        } else {
          durBadge.className = "inline-flex items-center gap-1 text-[10px] font-extrabold text-amber-700 bg-amber-100/80 px-2 py-0.5 rounded-md mt-1";
          durBadge.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> <span>Dài hơn giờ rảnh ban đầu</span>`;
        }
      }
    }

    summary.innerText = result.summary || "Lộ trình 3 trạm thuận đường tối ưu do hệ thống sắp xếp.";

    if (btnGmaps && result.gmaps_multi_url) {
      btnGmaps.href = result.gmaps_multi_url;
    }

    // Vẽ bản đồ Leaflet
    renderItineraryMap(result.start_coords, result.steps);

    // Render Timeline
    container.innerHTML = "";
    result.steps.forEach((s, idx) => {
      container.innerHTML += `
        <div class="flex items-start gap-3.5 bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-[#E11D48]/40 transition">
          <div class="w-8 h-8 rounded-xl bg-[#E11D48] text-white flex items-center justify-center font-black text-xs shadow-sm flex-shrink-0 mt-0.5">
            ${idx + 1}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-1">
              <h4 class="font-extrabold text-slate-900 text-xs sm:text-sm">${s.action}</h4>
              <span class="text-[11px] font-bold text-[#E11D48] bg-rose-50 px-2.5 py-0.5 rounded-lg whitespace-nowrap border border-rose-200/80">${s.time}</span>
            </div>
            <p class="font-black text-sm text-slate-900 mt-1.5">${s.location}</p>

            ${s.rule_explanation ? `
              <div class="mt-2.5 text-[11px] bg-amber-50/80 border border-amber-200/90 text-amber-900 p-2.5 rounded-xl flex items-start gap-2 shadow-2xs font-semibold">
                <i class="fa-solid fa-scale-balanced text-amber-600 text-xs mt-0.5 flex-shrink-0"></i>
                <div class="leading-relaxed">
                  <span class="font-extrabold uppercase text-[10px] tracking-wider text-amber-700 block mb-0.5">Tiêu chí Rule-based (G6-FR10):</span>
                  <span>${s.rule_explanation}</span>
                </div>
              </div>
            ` : ''}

            ${s.ai_reason ? `
              <div class="mt-2.5 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200 text-slate-700 shadow-2xs">
                <div class="text-[10px] font-bold text-[#E11D48] uppercase flex items-center gap-1 mb-1">
                  <i class="fa-solid fa-sparkles text-[#E11D48]"></i> Trợ lý AI Curation & Mẹo trải nghiệm (G6-FR11):
                </div>
                <div class="leading-relaxed font-medium">${s.ai_reason}</div>
                ${s.must_try_tip ? `<div class="mt-2 text-[11px] font-bold text-emerald-800 flex items-start gap-1 pt-1.5 border-t border-slate-200"><i class="fa-solid fa-lightbulb text-amber-500 mt-0.5"></i> <span>Gợi ý trải nghiệm: ${s.must_try_tip}</span></div>` : ''}
              </div>
            ` : ''}

            <div class="flex flex-wrap items-center gap-2 text-[11px] text-slate-500 mt-2.5">
              <span>🛵 ${s.travel_info}</span>
              <span>•</span>
              <span>💰 ${s.price_range}</span>
              <span>•</span>
              <span>🕒 ${s.open_hours}</span>
            </div>
            ${s.traffic_warning ? `<p class="text-[11px] text-amber-900 bg-amber-50 border border-amber-200 p-2.5 rounded-xl mt-2 font-medium">⚠️ <strong>Lưu ý:</strong> ${s.traffic_warning}</p>` : ''}
            
            <div class="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between">
              <span class="text-[10px] text-slate-400 font-semibold">Trạm dừng #${idx + 1} trên lộ trình</span>
              ${s.place_id ? `
                <button onclick="openPlaceDetailById(${s.place_id})" class="text-[11px] font-bold text-[#E11D48] hover:underline flex items-center gap-1 cursor-pointer">
                  <i class="fa-solid fa-circle-info text-[10px]"></i> <span>Xem chi tiết quán & review</span>
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    });

    resultArea.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alert("❌ Lỗi: " + err.message);
  } finally {
    btn.innerHTML = `<i class="fa-solid fa-route"></i> <span>Tạo Lịch Trình Khám Phá</span>`;
    btn.disabled = false;
  }
}

function shuffleAIItinerary() {
  aiShuffleSeed++;
  requestAIItinerary(true);
}

function handleAutoRelaxConstraint() {
  if (window._currentRelaxAction) {
    if (window._currentRelaxAction.time) {
      document.getElementById("aiTime").value = window._currentRelaxAction.time;
    }
    if (window._currentRelaxAction.budget) {
      selectAIBudget("100k_250k", window._currentRelaxAction.budget);
    }
  } else {
    document.getElementById("aiTime").value = "14:00 - 18:30";
    selectAIBudget("100k_250k", 250000);
  }
  requestAIItinerary(false);
}

// ==============================================================================
// 5. TỰ CHỌN ĐỊA ĐIỂM (TAB 2: 40 QUÁN CHUẨN XÁC, ĐỊNH VỊ GPS, BỘ LỌC BÁN KÍNH & A-Z)
// ==============================================================================

let exploreUserCoords = null;

// Bảng tọa độ các địa danh nổi tiếng tại Sài Gòn để nhận diện tức thì (0ms)
const KNOWN_SG_LANDMARKS = {
  "su pham": { name: "ĐH Sư Phạm TP.HCM (280 An Dương Vương)", lat: 10.7601, lon: 106.6823 },
  "280 an duong vuong": { name: "280 An Dương Vương, TP.HCM", lat: 10.7601, lon: 106.6823 },
  "an duong vuong": { name: "280 An Dương Vương, TP.HCM", lat: 10.7601, lon: 106.6823 },
  "an dong": { name: "Chợ An Đông, TP.HCM", lat: 10.7573, lon: 106.6713 },
  "cho an dong": { name: "Chợ An Đông, TP.HCM", lat: 10.7573, lon: 106.6713 },
  "thuan kieu": { name: "Thuận Kiều Plaza (190 Hồng Bàng)", lat: 10.7554, lon: 106.6577 },
  "binh tay": { name: "Chợ Bình Tây, TP.HCM", lat: 10.7497, lon: 106.6515 },
  "cho binh tay": { name: "Chợ Bình Tây, TP.HCM", lat: 10.7497, lon: 106.6515 },
  "ben thanh": { name: "Chợ Bến Thành, TP.HCM", lat: 10.7725, lon: 106.6980 },
  "cho ben thanh": { name: "Chợ Bến Thành, TP.HCM", lat: 10.7725, lon: 106.6980 },
  "nha tho duc ba": { name: "Nhà Thờ Đức Bà, TP.HCM", lat: 10.7798, lon: 106.6990 },
  "pho di bo": { name: "Phố Đi Bộ Nguyễn Huệ, TP.HCM", lat: 10.7744, lon: 106.7032 },
  "ho con rua": { name: "Hồ Con Rùa, TP.HCM", lat: 10.7828, lon: 106.6958 },
  "cho ray": { name: "Bệnh viện Chợ Rẫy (Nguyễn Chí Thanh)", lat: 10.7577, lon: 106.6596 },
  "benh vien cho ray": { name: "Bệnh viện Chợ Rẫy", lat: 10.7577, lon: 106.6596 },
  "y duoc": { name: "ĐH Y Dược TP.HCM (Hồng Bàng)", lat: 10.7562, lon: 106.6589 },
  "dai hoc y duoc": { name: "ĐH Y Dược TP.HCM", lat: 10.7562, lon: 106.6589 },
  "van lang": { name: "Công viên Văn Lang, TP.HCM", lat: 10.7585, lon: 106.6705 },
  "cong vien van lang": { name: "Công viên Văn Lang, TP.HCM", lat: 10.7585, lon: 106.6705 },
  "hung vuong": { name: "Hùng Vương Plaza (Hồng Bàng)", lat: 10.7570, lon: 106.6625 },
  "dai the gioi": { name: "Công viên Nước Đại Thế Giới", lat: 10.7530, lon: 106.6690 }
};

function removeVietnameseTones(str) {
  if (!str) return "";
  str = str.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  str = str.replace(/[đĐ]/g, "d");
  return str.toLowerCase().trim();
}

function calculateHaversineDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371; // Bán kính Trái Đất (km)
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// 1. Lấy vị trí GPS hiện tại cho Tab Tự Chọn
function getExploreGPSLocation() {
  const btn = document.getElementById("btnExploreGPS");
  const input = document.getElementById("exploreLocationInput");
  const badge = document.getElementById("exploreGpsStatusBadge");
  const clearBtn = document.getElementById("btnClearExploreLoc");

  if (!navigator.geolocation) {
    alert("Trình duyệt của bạn không hỗ trợ định vị GPS Geolocation.");
    return;
  }

  if (btn) {
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang lấy GPS...</span>`;
    btn.disabled = true;
  }

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      exploreUserCoords = {
        lat: pos.coords.latitude,
        lon: pos.coords.longitude
      };
      // Đồng bộ sang bên Lộ trình AI
      userGPSCoords = { ...exploreUserCoords };
      const aiInput = document.getElementById("aiStartLoc");
      if (aiInput && !aiInput.value.includes("GPS")) {
        aiInput.value = `Vị trí GPS hiện tại (${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)})`;
        const aiIcon = document.getElementById("gpsStatusIcon");
        if (aiIcon) aiIcon.classList.remove("hidden");
      }

      if (input) input.value = `Vị trí GPS hiện tại (${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)})`;
      if (badge) badge.classList.remove("hidden");
      if (clearBtn) clearBtn.classList.remove("hidden");
      if (btn) {
        btn.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-300"></i> <span>Đã nhận GPS</span>`;
        btn.disabled = false;
      }

      // Tự động sắp xếp gần nhất trước
      const sortSelect = document.getElementById("allSortFilter");
      if (sortSelect && sortSelect.value === "default") {
        sortSelect.value = "distance_asc";
      }

      filterAllPlaces();
    },
    (err) => {
      alert("Không thể lấy vị trí GPS: " + err.message + ". Bạn có thể điền địa chỉ hoặc bấm vào các mốc gợi ý bên dưới!");
      if (btn) {
        btn.innerHTML = `<i class="fa-solid fa-crosshairs"></i> <span>Dùng GPS hiện tại</span>`;
        btn.disabled = false;
      }
    },
    { timeout: 8000, enableHighAccuracy: true }
  );
}

// 2. Chọn mốc vị trí gợi ý nhanh
function setExploreLocationPreset(label, lat, lon) {
  exploreUserCoords = { lat, lon };
  const input = document.getElementById("exploreLocationInput");
  const badge = document.getElementById("exploreGpsStatusBadge");
  const clearBtn = document.getElementById("btnClearExploreLoc");
  const btn = document.getElementById("btnExploreGPS");

  if (input) input.value = label;
  if (badge) badge.classList.remove("hidden");
  if (clearBtn) clearBtn.classList.remove("hidden");
  if (btn) btn.innerHTML = `<i class="fa-solid fa-location-dot"></i> <span>Đã chọn mốc</span>`;

  const sortSelect = document.getElementById("allSortFilter");
  if (sortSelect && sortSelect.value === "default") {
    sortSelect.value = "distance_asc";
  }

  filterAllPlaces();
}

// 3. Xử lý khi người dùng tự gõ địa chỉ
async function onExploreLocationInputChange() {
  const input = document.getElementById("exploreLocationInput");
  const val = input ? input.value.trim() : "";
  if (!val) {
    clearExploreLocation();
    return;
  }

  const norm = removeVietnameseTones(val);
  let foundCoords = null;

  for (const k of Object.keys(KNOWN_SG_LANDMARKS)) {
    if (norm.includes(k)) {
      foundCoords = { lat: KNOWN_SG_LANDMARKS[k].lat, lon: KNOWN_SG_LANDMARKS[k].lon };
      break;
    }
  }

  if (!foundCoords) {
    try {
      const q = encodeURIComponent(`${val}, Ho Chi Minh City, Vietnam`);
      const resp = await fetch(`https://nominatim.openstreetmap.org/search?q=${q}&format=json&limit=1`, {
        headers: { "Accept-Language": "vi" }
      });
      const data = await resp.json();
      if (data && data.length > 0) {
        foundCoords = { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
      }
    } catch (e) {
      console.warn("Geocoding address error:", e);
    }
  }

  if (!foundCoords) {
    foundCoords = { lat: 10.7554, lon: 106.6577 };
  }

  exploreUserCoords = foundCoords;
  const badge = document.getElementById("exploreGpsStatusBadge");
  const clearBtn = document.getElementById("btnClearExploreLoc");
  if (badge) badge.classList.remove("hidden");
  if (clearBtn) clearBtn.classList.remove("hidden");

  const sortSelect = document.getElementById("allSortFilter");
  if (sortSelect && sortSelect.value === "default") {
    sortSelect.value = "distance_asc";
  }

  filterAllPlaces();
}

// 4. Hủy vị trí định vị
function clearExploreLocation() {
  exploreUserCoords = null;
  const input = document.getElementById("exploreLocationInput");
  const badge = document.getElementById("exploreGpsStatusBadge");
  const clearBtn = document.getElementById("btnClearExploreLoc");
  const btn = document.getElementById("btnExploreGPS");
  const radiusSelect = document.getElementById("allRadiusFilter");

  if (input) input.value = "";
  if (badge) badge.classList.add("hidden");
  if (clearBtn) clearBtn.classList.add("hidden");
  if (btn) btn.innerHTML = `<i class="fa-solid fa-crosshairs"></i> <span>Dùng GPS hiện tại</span>`;
  if (radiusSelect) radiusSelect.value = "all";

  const sortSelect = document.getElementById("allSortFilter");
  if (sortSelect && sortSelect.value === "distance_asc") {
    sortSelect.value = "default";
  }

  filterAllPlaces();
}

// Hàm thông báo nhắc nhở khi chức năng yêu cầu vị trí GPS/điểm mốc
function showLocationRequiredNotice(actionType) {
  const isSort = (actionType === "sort");
  const msg = isSort
    ? "📍 Bạn chưa chọn vị trí!\n\nĐể sắp xếp các quán theo 'Khoảng cách: Gần nhất', bạn hãy bấm 'Dùng GPS hiện tại' hoặc bấm chọn một điểm mốc (Hồ Con Rùa, Chợ An Đông,...) ở khung định vị phía trên nhé!"
    : "📍 Bạn chưa chọn vị trí!\n\nĐể lọc các quán trong bán kính mong muốn, bạn hãy bấm 'Dùng GPS hiện tại' hoặc nhập vị trí của bạn ở khung định vị phía trên nhé!";

  alert(msg);

  // Cuộn mượt và highlight khung định vị để người dùng bắt mắt ngay
  const locInput = document.getElementById("exploreLocationInput");
  const locCard = locInput ? locInput.closest(".bg-white") : null;
  if (locCard) {
    locCard.scrollIntoView({ behavior: "smooth", block: "center" });
    locCard.classList.add("ring-4", "ring-[#E11D48]/40", "transition-all", "duration-500");
    setTimeout(() => {
      locCard.classList.remove("ring-4", "ring-[#E11D48]/40");
    }, 2500);
  }
  if (locInput) {
    locInput.focus();
  }
}

// Xử lý khi người dùng đổi lựa chọn Sắp xếp
function handleSortFilterChange() {
  const sortSelect = document.getElementById("allSortFilter");
  const sortVal = sortSelect?.value;
  if (sortVal === "distance_asc" && !exploreUserCoords) {
    showLocationRequiredNotice("sort");
    sortSelect.value = "default";
    return;
  }
  filterAllPlaces();
}

// 5. Khi người dùng thay đổi bộ lọc bán kính
function onRadiusFilterChange() {
  const radiusSelect = document.getElementById("allRadiusFilter");
  const radius = radiusSelect?.value || "all";
  if (radius !== "all" && !exploreUserCoords) {
    showLocationRequiredNotice("radius");
    radiusSelect.value = "all";
    return;
  }
  filterAllPlaces();
}

// ==============================================================================
// TAB 2: THẺ CATALOG DU LỊCH 2 CỘT CÂN ĐỐI (DÀNH CHO TAB TỰ CHỌN 40 QUÁN)
// THIẾT KẾ DẠNG GRID THOÁNG ĐÃNG, KHÔNG BỊ TRÙNG LẶP KIỂU TAB 1
// ==============================================================================
function buildCatalogCardHTML(p) {
  const isEat = p.category === "an_uong";
  const isOpen = isPlaceCurrentlyOpen(p.open_time, p.close_time);
  const gmapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.name + ' ' + p.address)}`;

  const priceText = p.price_display
    ? p.price_display
    : ((p.min_price === 0 && p.max_price === 0)
      ? "Miễn phí vé"
      : `${p.min_price ? p.min_price.toLocaleString() + 'đ' : ''} – ${p.max_price ? p.max_price.toLocaleString() + 'đ' : ''}`);

  let distanceHTML = "";
  if (typeof p.distanceKm === "number" && !isNaN(p.distanceKm) && exploreUserCoords) {
    const isWalk = p.distanceKm <= 0.6;
    const distStr = p.distanceKm < 1 ? `${Math.round(p.distanceKm * 1000)}m` : `${p.distanceKm.toFixed(1)} km`;
    distanceHTML = `
      <span class="px-2 py-0.5 rounded-md text-[10px] font-extrabold ${isWalk ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-blue-50 text-blue-800 border border-blue-200'} whitespace-nowrap inline-flex items-center gap-1">
        <i class="fa-solid ${isWalk ? 'fa-person-walking' : 'fa-motorcycle'} text-[10px]"></i>
        <span>${distStr}</span>
      </span>
    `;
  }

  const imageHtml = renderPlaceImage(p, "w-full", "h-full");

  return `
    <div class="catalog-card-v3">
      <!-- 1. Header ảnh quán tỷ lệ vàng chuẩn -->
      <div onclick="openPlaceDetailById(${p.id})" class="card-image-box cursor-pointer group">
        ${imageHtml}
        <!-- Badge thể loại -->
        <span class="absolute top-2.5 left-2.5 text-[10px] font-black uppercase text-[#E11D48] bg-white/95 backdrop-blur-xs px-2.5 py-0.5 rounded-lg shadow-sm">
          ${isEat ? 'Ẩm Thực' : 'Đi Chơi'}
        </span>
        <!-- Badge mở cửa -->
        <span class="absolute top-2.5 right-2.5 text-[10px] font-black uppercase ${isOpen ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'} px-2.5 py-0.5 rounded-lg shadow-sm">
          ${isOpen ? '🟢 Mở cửa' : '🔴 Đóng cửa'}
        </span>
      </div>

      <!-- 2. Thân thẻ thông tin -->
      <div class="p-4 flex-1 flex flex-col justify-between">
        <div>
          <!-- Tên quán + Badge Số sao nổi bật ngay bên cạnh -->
          <div class="flex items-start justify-between gap-2 mb-1.5">
            <h4 onclick="openPlaceDetailById(${p.id})" class="font-black text-slate-900 text-sm leading-snug line-clamp-1 hover:text-[#E11D48] transition cursor-pointer" title="${p.name}">
              ${p.name}
            </h4>
            <div class="rating-pill-prominent py-0.5 px-2 text-xs flex-shrink-0">
              <i class="fa-solid fa-star text-amber-500 text-[11px]"></i>
              <span class="font-black">${p.rating}</span>
            </div>
          </div>

          <!-- Địa chỉ & Khoảng cách -->
          <div class="text-[11px] text-slate-500 font-medium flex items-center justify-between gap-1.5 mb-2.5" title="${p.address}">
            <span class="truncate flex items-center gap-1">
              <i class="fa-solid fa-location-dot text-[#E11D48] text-[11px] flex-shrink-0"></i>
              <span class="truncate">${p.address}</span>
            </span>
            ${distanceHTML}
          </div>

          <!-- Mức giá & Giờ cao điểm -->
          <div class="flex items-center justify-between text-[11px] font-bold py-1.5 px-2.5 bg-slate-50 rounded-xl mb-2 border border-slate-100">
            <span class="text-slate-800 truncate mr-2">💰 ${priceText}</span>
            <span class="text-amber-800 whitespace-nowrap">🕒 ${(p.peak_hours && p.peak_hours !== 'Chưa rõ') ? p.peak_hours.split('(')[0].trim() : 'Chưa rõ'}</span>
          </div>




        </div>

        <!-- 3. Chân thẻ hành động -->
        <div class="pt-2.5 border-t border-slate-100 flex items-center justify-between gap-1.5">
          <div class="flex items-center gap-1.5">
            <button onclick="openPlaceDetailById(${p.id})" title="Xem chi tiết" class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition flex items-center gap-1 cursor-pointer">
              <i class="fa-solid fa-circle-info text-[10px]"></i> <span>Chi tiết</span>
            </button>
            ${(currentUser && currentUser.role === 'admin') ? `
              <button onclick="openEditPlaceModalById(${p.id})" title="Sửa quán" class="px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1 cursor-pointer">
                <i class="fa-solid fa-pen-to-square text-[10px]"></i>
              </button>
            ` : ''}
          </div>

          <a href="${gmapsUrl}" target="_blank" title="Xem 100% đánh giá & ảnh trên Google Maps" class="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1 whitespace-nowrap shadow-xs">
            <i class="fa-brands fa-google text-xs"></i> <span>Maps thật</span> <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
          </a>
        </div>
      </div>
    </div>
  `;
}

function renderAllPlaces(places) {
  const container = document.getElementById("allPlacesGrid");
  container.innerHTML = "";

  if (!places || places.length === 0) {
    container.innerHTML = `<div class="col-span-full p-10 text-center text-xs text-slate-400 bg-white rounded-2xl border border-dashed border-slate-200">Không tìm thấy địa điểm nào khớp với bộ lọc & bán kính đã chọn.<br><button onclick="clearExploreLocation()" class="mt-2 text-[#E11D48] font-bold underline cursor-pointer">Xóa bộ lọc bán kính để xem tất cả</button></div>`;
    return;
  }

  places.forEach(p => {
    container.innerHTML += buildCatalogCardHTML(p);
  });
}

function removeVietnameseTones(str) {
  if (!str) return "";
  str = str.toLowerCase();
  str = str.replace(/à|á|ạ|ả|ã|â|ầ|ấ|ậ|ẩ|ẫ|ă|ằ|ắ|ặ|ẳ|ẵ/g, "a");
  str = str.replace(/è|é|ẹ|ẻ|ẽ|ê|ề|ế|ệ|ể|ễ/g, "e");
  str = str.replace(/ì|í|ị|ỉ|ĩ/g, "i");
  str = str.replace(/ò|ó|ọ|ỏ|õ|ô|ồ|ố|ộ|ổ|ỗ|ơ|ờ|ớ|ợ|ở|ỡ/g, "o");
  str = str.replace(/ù|ú|ụ|ủ|ũ|ư|ừ|ứ|ự|ử|ữ/g, "u");
  str = str.replace(/ỳ|ý|ỵ|ỷ|ỹ/g, "y");
  str = str.replace(/đ/g, "d");
  str = str.replace(/\u0300|\u0301|\u0303|\u0309|\u0323/g, "");
  str = str.replace(/\u02C6|\u0306|\u031B/g, "");
  return str.trim();
}

function checkPlacePriceMatch(p, price) {
  if (price === "all") return true;
  const minP = p.min_price || 0;
  const maxP = p.max_price || 0;
  const isFree = (minP === 0 && maxP === 0);

  if (price === "free") {
    return isFree;
  }
  if (price === "under_50k" || price === "50000") {
    return isFree || (maxP > 0 && maxP <= 65000) || (minP > 0 && minP <= 50000 && maxP <= 75000);
  }
  if (price === "50k_100k") {
    if (isFree) return false;
    return (minP >= 40000 && minP <= 100000) || (maxP >= 50000 && maxP <= 120000) || (minP < 50000 && maxP >= 60000 && maxP <= 120000);
  }
  if (price === "100k_250k") {
    if (isFree) return false;
    return (minP >= 90000 && minP <= 250000) || (maxP >= 100000 && maxP <= 280000) || (minP <= 100000 && maxP >= 150000 && maxP <= 300000);
  }
  if (price === "above_250k") {
    if (isFree) return false;
    return (maxP >= 250000 || minP >= 200000);
  }
  if (price === "100000") {
    return isFree || minP <= 100000;
  }
  if (price === "250000") {
    return isFree || minP <= 250000;
  }
  return true;
}

function filterAllPlaces() {
  const q = document.getElementById("allSearchInput")?.value.trim() || "";
  const cat = document.getElementById("allCategoryFilter")?.value || "all";
  const tag = document.getElementById("allTagFilter")?.value || "all";
  const price = document.getElementById("allPriceFilter")?.value || "all";
  const sort = document.getElementById("allSortFilter")?.value || "default";
  const radius = document.getElementById("allRadiusFilter")?.value || "all";
  const radiusNum = radius !== "all" ? parseInt(radius) : null;

  // Cập nhật thông tin khoảng cách cho tất cả quán nếu đã có tọa độ
  allPlacesCache.forEach(p => {
    if (exploreUserCoords && p.lat && p.lon) {
      p.distanceKm = calculateHaversineDistanceKm(
        exploreUserCoords.lat,
        exploreUserCoords.lon,
        parseFloat(p.lat),
        parseFloat(p.lon)
      );
    } else {
      delete p.distanceKm;
    }
  });

  const normQ = removeVietnameseTones(q);

  let filtered = allPlacesCache.filter(p => {
    // 1. Tìm kiếm thông minh (có dấu và không dấu tiếng Việt)
    let matchQ = true;
    if (normQ) {
      const normName = removeVietnameseTones(p.name || "");
      const normAddr = removeVietnameseTones(p.address || "");
      matchQ = normName.includes(normQ) || normAddr.includes(normQ);
    }

    // 2. Thể loại (Chỉ có 2 thể loại cốt lõi: Ẩm thực hoặc Đi chơi)
    const matchCat = (cat === "all") || (p.category === cat);

    // 3. Bối cảnh 2-Tier
    const pTiers = parsePlaceTiers(p.tags);
    const matchTag = (tag === "all") || pTiers.tier1.includes(tag) || pTiers.tier2.includes(tag);

    // 4. Mức giá chuẩn xác
    const matchPrice = checkPlacePriceMatch(p, price);

    // 5. Admin pick
    const matchAdminPick = (sort !== "admin_pick") || (p.is_admin_choice === 1);

    // 6. Lọc theo bán kính mét (nếu có vị trí)
    let matchRadius = true;
    if (radiusNum !== null) {
      if (typeof p.distanceKm === "number") {
        matchRadius = (p.distanceKm * 1000) <= radiusNum;
      } else {
        matchRadius = false;
      }
    }

    return matchQ && matchCat && matchTag && matchPrice && matchAdminPick && matchRadius;
  });

  // Sắp xếp
  if (sort === "distance_asc") {
    filtered.sort((a, b) => {
      const distA = typeof a.distanceKm === "number" ? a.distanceKm : 9999;
      const distB = typeof b.distanceKm === "number" ? b.distanceKm : 9999;
      return distA - distB;
    });
  } else if (sort === "rating_desc") {
    filtered.sort((a, b) => (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0));
  } else if (sort === "rating_asc") {
    filtered.sort((a, b) => (parseFloat(a.rating) || 0) - (parseFloat(b.rating) || 0));
  } else if (sort === "price_desc") {
    // Sắp xếp mức giá từ lớn tới bé (Cao đến thấp)
    filtered.sort((a, b) => {
      const pA = a.max_price || a.min_price || 0;
      const pB = b.max_price || b.min_price || 0;
      if (pB !== pA) return pB - pA;
      return (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0);
    });
  } else if (sort === "price_asc") {
    // Sắp xếp mức giá từ bé tới lớn (Thấp đến cao)
    filtered.sort((a, b) => {
      const pA = a.min_price || a.max_price || 0;
      const pB = b.min_price || b.max_price || 0;
      if (pA !== pB) return pA - pB;
      return (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0);
    });
  } else if (tag !== "all") {
    // Sắp xếp ưu tiên chuẩn 2-Tier: Quán có tag ở Tier 1 lên đầu, Tier 2 xếp sau, trong cùng Tier xếp theo rating cao
    filtered.sort((a, b) => {
      const tA = parsePlaceTiers(a.tags);
      const tB = parsePlaceTiers(b.tags);
      const rankA = tA.tier1.includes(tag) ? 1 : (tA.tier2.includes(tag) ? 2 : 3);
      const rankB = tB.tier1.includes(tag) ? 1 : (tB.tier2.includes(tag) ? 2 : 3);
      if (rankA !== rankB) return rankA - rankB;
      return (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0);
    });
  } else if (price !== "all") {
    // Khi đang lọc theo mức giá (ví dụ Dưới 50k) và sắp xếp là Mặc định: Tự động sắp xếp từ lớn tới bé
    filtered.sort((a, b) => {
      const pA = a.max_price || a.min_price || 0;
      const pB = b.max_price || b.min_price || 0;
      if (pB !== pA) return pB - pA;
      return (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0);
    });
  } else {
    // Mặc định: Quán Admin yêu thích lên đầu, sau đó theo Rating cao nhất
    filtered.sort((a, b) => {
      if ((b.is_admin_choice || 0) !== (a.is_admin_choice || 0)) {
        return (b.is_admin_choice || 0) - (a.is_admin_choice || 0);
      }
      return (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0);
    });
  }

  // Cập nhật thanh đếm kết quả
  const countEl = document.getElementById("filteredPlacesCount");
  if (countEl) countEl.innerText = filtered.length;

  const radiusNotice = document.getElementById("activeRadiusNotice");
  if (radiusNotice) {
    if (radiusNum !== null && exploreUserCoords) {
      const radiusLabel = radiusNum < 1000 ? `${radiusNum} mét` : `${(radiusNum / 1000).toFixed(0)} km`;
      radiusNotice.innerHTML = `🎯 Đang lọc trong bán kính <strong>${radiusLabel}</strong> (${filtered.length} quán)`;
      radiusNotice.classList.remove("hidden");
    } else {
      radiusNotice.classList.add("hidden");
    }
  }

  renderAllPlaces(filtered);
}

// Chức năng lưu quán yêu thích đã được xóa theo yêu cầu

// ==============================================================================
// 6. TRANG QUẢN TRỊ ADMIN (BỘ LỌC A-Z, TRÍCH XUẤT GOOGLE MAPS & CHỈNH ẢNH)
// ==============================================================================

let currentAdminSubTab = "places";

function switchAdminSubTab(subTab) {
  currentAdminSubTab = subTab;
  const btnPlaces = document.getElementById("adminSubTabPlaces");
  const btnUsers = document.getElementById("adminSubTabUsers");
  const btnTags = document.getElementById("adminSubTabTags");
  const secPlaces = document.getElementById("adminSectionPlaces");
  const secUsers = document.getElementById("adminSectionUsers");
  const secTags = document.getElementById("adminSectionTags");

  [btnPlaces, btnUsers, btnTags].forEach(b => { if (b) b.className = "admin-subtab-btn"; });
  [secPlaces, secUsers, secTags].forEach(s => { if (s) s.classList.add("hidden"); });

  if (subTab === "places") {
    if (btnPlaces) btnPlaces.className = "admin-subtab-btn active";
    if (secPlaces) secPlaces.classList.remove("hidden");
  } else if (subTab === "users") {
    if (btnUsers) btnUsers.className = "admin-subtab-btn active";
    if (secUsers) secUsers.classList.remove("hidden");
    loadAdminUsers();
  } else if (subTab === "tags") {
    if (btnTags) btnTags.className = "admin-subtab-btn active";
    if (secTags) secTags.classList.remove("hidden");
    loadAdminTags();
  }
}

async function loadAdminUsers() {
  try {
    const res = await fetch(`${API_BASE}/admin/users`);
    const users = await res.json();
    const countBadge = document.getElementById("adminUserCountBadge");
    const statUsers = document.getElementById("statTotalUsers");
    if (countBadge) countBadge.innerText = users.length;
    if (statUsers) statUsers.innerText = users.length;

    renderAdminUsersTable(users);
  } catch (e) {
    console.error("Lỗi tải danh sách người dùng:", e);
  }
}

function renderAdminUsersTable(users) {
  const tbody = document.getElementById("adminUsersTable");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!users || users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-stone-400">Không có tài khoản người dùng nào.</td></tr>`;
    return;
  }

  users.forEach(u => {
    const isAdmin = u.role === "admin";
    const isSelf = currentUser && currentUser.id === u.id;

    tbody.innerHTML += `
      <tr class="hover:bg-stone-50/70 transition border-b border-stone-100">
        <td class="p-3.5 font-mono font-bold text-stone-400 whitespace-nowrap">#${u.id}</td>
        <td class="p-3.5 font-extrabold text-stone-900 whitespace-nowrap">${u.full_name} ${isSelf ? '<span class="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 ml-1">Bạn</span>' : ''}</td>
        <td class="p-3.5 font-mono text-stone-600 whitespace-nowrap">@${u.username}</td>
        <td class="p-3.5 whitespace-nowrap">
          <span class="px-2.5 py-1 rounded-md text-[10px] font-black uppercase ${isAdmin ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-stone-100 text-stone-700 border border-stone-200'}">
            <i class="fa-solid ${isAdmin ? 'fa-user-gear' : 'fa-user'} mr-1"></i>
            ${isAdmin ? 'Quản Trị Viên' : 'Thành Viên'}
          </span>
        </td>
        <td class="p-3.5 text-stone-400 text-xs whitespace-nowrap">${u.created_at ? u.created_at.split('T')[0] : 'Ban đầu'}</td>
        <td class="p-3.5 text-center whitespace-nowrap bg-stone-50/50 border-l border-stone-100">
          <div class="flex items-center justify-center gap-1.5">
            <button onclick="toggleUserRole(${u.id}, '${u.role}')" class="px-3 py-1.5 ${isAdmin ? 'bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200' : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200'} rounded-xl font-bold text-xs flex items-center gap-1 transition cursor-pointer" title="Đổi quyền hạn">
              <i class="fa-solid ${isAdmin ? 'fa-arrow-down' : 'fa-arrow-up'} text-[10px]"></i>
              <span>${isAdmin ? 'Hạ quyền User' : 'Nâng quyền Admin'}</span>
            </button>
            <button onclick="handleDeleteUser(${u.id}, '${u.username}')" ${isSelf ? 'disabled' : ''} class="px-2.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 disabled:opacity-30 rounded-xl font-bold text-xs flex items-center gap-1 transition cursor-pointer" title="${isSelf ? 'Không thể tự xóa tài khoản đang đăng nhập' : 'Xóa tài khoản này'}">
              <i class="fa-solid fa-trash text-[11px]"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  });
}

async function toggleUserRole(userId, currentRole) {
  const newRole = currentRole === "admin" ? "user" : "admin";
  const label = newRole === "admin" ? "Quản trị viên (Admin)" : "Thành viên thông thường (User)";
  if (!confirm(`Bạn có chắc muốn đổi vai trò của tài khoản này thành ${label}?`)) return;

  try {
    const res = await fetch(`${API_BASE}/admin/users/${userId}/role`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: newRole })
    });
    const data = await res.json();
    if (!res.ok) {
      alert("Lỗi: " + (data.detail || "Không thể cập nhật vai trò"));
      return;
    }
    alert(data.message || "Cập nhật vai trò thành công!");
    loadAdminUsers();
    // Nếu đổi chính tài khoản đang đăng nhập
    if (currentUser && currentUser.id === userId) {
      currentUser.role = newRole;
      localStorage.setItem("sggo_user", JSON.stringify(currentUser));
      updateAuthUI();
    }
  } catch (e) {
    alert("Lỗi kết nối máy chủ");
  }
}

async function handleDeleteUser(userId, username) {
  if (!confirm(`Cảnh báo: Bạn có chắc muốn xóa vĩnh viễn tài khoản @${username}? Thao tác này không thể hoàn tác.`)) return;

  try {
    const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
      method: "DELETE"
    });
    const data = await res.json();
    if (!res.ok) {
      alert("Lỗi: " + (data.detail || "Không thể xóa tài khoản"));
      return;
    }
    alert(data.message || "Đã xóa tài khoản thành công!");
    loadAdminUsers();
  } catch (e) {
    alert("Lỗi kết nối máy chủ");
  }
}

async function loadAdminDashboard() {
  if (!currentUser || currentUser.role !== "admin") {
    alert("Chỉ Quản trị viên (Admin) mới có quyền truy cập khu vực này!");
    switchMode("flow");
    return;
  }

  try {
    const statsRes = await fetch(`${API_BASE}/admin/stats`);
    const stats = await statsRes.json();
    if (document.getElementById("statTotalPlaces")) document.getElementById("statTotalPlaces").innerText = stats.total_places;
    if (document.getElementById("statVerifiedPlaces")) document.getElementById("statVerifiedPlaces").innerText = stats.verified_places;
    if (document.getElementById("statTotalUsers")) document.getElementById("statTotalUsers").innerText = stats.total_users;
    if (document.getElementById("statTotalFavorites")) document.getElementById("statTotalFavorites").innerText = stats.total_favorites;
  } catch (e) {}

  try {
    const placesRes = await fetch(`${API_BASE}/places?include_hidden=true`);
    allPlacesCache = await placesRes.json();
    renderAdminPlacesTable(allPlacesCache);
    populateQuickEditSelect(allPlacesCache);
  } catch (e) {}

  loadAdminUsers();
}

function populateQuickEditSelect(places) {
  const sel = document.getElementById("quickEditPlaceSelect");
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = `<option value="">-- Chọn quán cần chỉnh sửa ngay (${places.length} quán) --</option>`;
  places.forEach(p => {
    const isEat = p.category === "an_uong";
    sel.innerHTML += `<option value="${p.id}">#${p.id} - ${p.name} (${isEat ? 'Ẩm thực' : 'Đi chơi'})</option>`;
  });
  if (currentVal) sel.value = currentVal;
}

function handleQuickSelectEdit(placeId) {
  if (!placeId) return;
  openEditPlaceModalById(parseInt(placeId));
  const sel = document.getElementById("quickEditPlaceSelect");
  if (sel) sel.value = "";
}

function renderAdminPlacesTable(places) {
  const tbody = document.getElementById("adminPlacesTable");
  const countEl = document.getElementById("adminFilteredCount");
  tbody.innerHTML = "";

  if (countEl) countEl.innerText = `Hiển thị ${places.length} địa điểm`;

  if (!places || places.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400">Không có địa điểm nào khớp với bộ lọc.</td></tr>`;
    return;
  }

  places.forEach(p => {
    const isEat = p.category === "an_uong";
    const isHidden = (p.is_hidden === 1);
    const imageHtml = renderPlaceImage(p, "w-12", "h-10");

    tbody.innerHTML += `
      <tr class="hover:bg-blue-50/40 transition border-b border-slate-100 ${isHidden ? 'bg-slate-50/80 opacity-75' : ''}">
        <td class="p-3 font-mono font-bold text-slate-400 whitespace-nowrap">#${p.id}</td>
        <td class="p-3 whitespace-nowrap">
          <div class="w-12 h-10 flex-shrink-0">
            ${imageHtml}
          </div>
        </td>
        <td class="p-3 min-w-[190px] max-w-[260px]">
          <div class="font-extrabold text-slate-900 truncate flex items-center gap-1.5" title="${p.name}">
            <span class="truncate">${p.name}</span>
            ${p.is_admin_choice === 1 ? '<span class="text-[9px] bg-amber-100 text-amber-900 font-extrabold px-1.5 py-0.5 rounded border border-amber-300 whitespace-nowrap flex items-center gap-0.5"><i class="fa-solid fa-crown text-amber-600"></i> Pick</span>' : ''}
            ${isHidden ? '<span class="text-[9px] bg-rose-100 text-rose-700 font-extrabold px-1.5 py-0.5 rounded border border-rose-200 whitespace-nowrap flex items-center gap-0.5"><i class="fa-solid fa-eye-slash"></i> Đã ẩn</span>' : '<span class="text-[9px] bg-emerald-50 text-emerald-700 font-bold px-1.5 py-0.5 rounded border border-emerald-200 whitespace-nowrap flex items-center gap-0.5"><i class="fa-solid fa-eye"></i> Hiện</span>'}
          </div>
          <div class="text-[11px] text-slate-400 truncate" title="${p.address}">${p.address}</div>
        </td>
        <td class="p-3 whitespace-nowrap">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${isEat ? 'bg-rose-50 text-[#E11D48]' : 'bg-teal-50 text-teal-700'}">
            ${isEat ? '🍜 Ăn uống' : '📸 Đi chơi'}
          </span>
        </td>
        <td class="p-3 font-medium whitespace-nowrap text-slate-600">${(p.min_price === 0 && p.max_price === 0) ? 'Miễn phí' : `${p.min_price.toLocaleString()}đ - ${p.max_price.toLocaleString()}đ`}</td>
        <td class="p-3 whitespace-nowrap">
          <span class="font-bold text-amber-600">⭐ ${p.rating}</span>
          <div class="text-[10px] text-slate-400 font-normal">${p.open_time} - ${p.close_time}</div>
        </td>
        <td class="p-3 text-center whitespace-nowrap bg-blue-50/30 border-l border-blue-100">
          <div class="flex items-center justify-center gap-1.5">
            <button onclick="handleToggleHidePlace(${p.id}, ${isHidden ? 0 : 1})" class="px-2.5 py-1.5 rounded-xl font-bold text-xs flex items-center gap-1 transition shadow-xs cursor-pointer ${isHidden ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-slate-200 hover:bg-slate-300 text-slate-700'}" title="${isHidden ? 'Hiện lại quán này trên trang người dùng' : 'Ẩn quán này khỏi trang người dùng'}">
              <i class="fa-solid ${isHidden ? 'fa-eye' : 'fa-eye-slash'}"></i> <span>${isHidden ? 'Hiện lại' : 'Ẩn quán'}</span>
            </button>
            <button onclick="openEditPlaceModalById(${p.id})" class="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-xs flex items-center gap-1 transition shadow-xs cursor-pointer" title="Chỉnh sửa toàn bộ thông tin quán này">
              <i class="fa-solid fa-pen-to-square"></i> <span>Sửa</span>
            </button>
            <button onclick="handleDeletePlaceById(${p.id})" class="px-2 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-xl font-bold text-xs flex items-center gap-1 transition cursor-pointer" title="Xóa địa điểm">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  });
}

async function handleToggleHidePlace(placeId, targetHidden) {
  try {
    const res = await fetch(`${API_BASE}/admin/places/${placeId}/toggle-hide`, {
      method: "POST"
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Không thể thay đổi trạng thái ẩn.");
    }
    const data = await res.json();
    const p = allPlacesCache.find(x => Number(x.id) === Number(placeId));
    if (p) p.is_hidden = data.place.is_hidden;
    filterAdminTable();
  } catch (err) {
    alert("Lỗi: " + err.message);
  }
}

// BỘ LỌC TỪ A ĐẾN Z CHO ADMIN (BAO GỒM LỌC REVIEW THẬT / MẪU VÀ TRẠNG THÁI ẨN / HIỆN)
function filterAdminTable() {
  const q = document.getElementById("adminSearchInput")?.value.trim() || "";
  const cat = document.getElementById("adminCategoryFilter")?.value || "all";
  const rating = document.getElementById("adminRatingFilter")?.value || "all";
  const price = document.getElementById("adminPriceFilter")?.value || "all";
  const status = document.getElementById("adminStatusFilter")?.value || "all";

  const normQ = removeVietnameseTones(q);

  const filtered = allPlacesCache.filter(p => {
    let matchQ = true;
    if (normQ) {
      const normName = removeVietnameseTones(p.name || "");
      const normAddr = removeVietnameseTones(p.address || "");
      matchQ = normName.includes(normQ) || normAddr.includes(normQ);
    }

    const matchCat = (cat === "all") || (p.category === cat);
    const matchRating = (rating === "all") || (p.rating >= parseFloat(rating));
    
    let matchPrice = true;
    if (price === "free") matchPrice = checkPlacePriceMatch(p, "free");
    else if (price === "50000") matchPrice = checkPlacePriceMatch(p, "under_50k");
    else if (price === "100000") matchPrice = checkPlacePriceMatch(p, "50k_100k") || checkPlacePriceMatch(p, "under_50k");
    else if (price === "above_100k") matchPrice = p.max_price >= 100000;

    let matchStatus = true;
    if (status === "visible") matchStatus = (!p.is_hidden || p.is_hidden === 0);
    else if (status === "hidden") matchStatus = (p.is_hidden === 1);

    return matchQ && matchCat && matchRating && matchPrice && matchStatus;
  });

  renderAdminPlacesTable(filtered);
}

// BÓC TÁCH LINK GOOGLE MAPS HOẶC TÊN QUÁN (ROBUST MULTI-PATTERN)
async function handleExtractGmaps() {
  const input = document.getElementById("gmapsExtractInput");
  const raw = input.value.trim();
  if (!raw) {
    alert("Vui lòng dán link Google Maps hoặc gõ tên quán vào ô bên trên!");
    return;
  }

  const btn = document.getElementById("btnExtractGmaps");
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang bóc tách...`;
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/admin/extract-gmaps`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url_or_query: raw })
    });
    
    if (!res.ok) {
      let errDetail = "Không thể bóc tách link này.";
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch (e) {}
      throw new Error(errDetail);
    }
    
    const data = await res.json();
    const p = data.place;

    // Tự động điền dữ liệu bóc tách vào form bên dưới
    document.getElementById("formName").value = p.name || "";
    document.getElementById("formCategory").value = p.category || "an_uong";
    document.getElementById("formAddress").value = p.address || "";
    document.getElementById("formDistrict").value = p.district || "TP.HCM";
    document.getElementById("formOpenTime").value = p.open_time || "08:00";
    document.getElementById("formCloseTime").value = p.close_time || "22:30";
    document.getElementById("formMinPrice").value = p.min_price || 30000;
    document.getElementById("formMaxPrice").value = p.max_price || 85000;
    document.getElementById("formRating").value = p.rating || 4.5;
    document.getElementById("formPeakHours").value = p.peak_hours || "Chưa rõ";
    // Đổ dữ liệu phân tầng 2-Tier vào checkbox
  const { tier1: curT1, tier2: curT2 } = parsePlaceTiers(p.tags || "");
  ['di_1_minh', 'hen_ho', 'nhom_ban', 'gia_dinh'].forEach(t => {
    const c1 = document.getElementById(`chk_t1_${t}`);
    const c2 = document.getElementById(`chk_t2_${t}`);
    if (c1) c1.checked = curT1.includes(t);
    if (c2) c2.checked = curT2.includes(t);
  });
  syncAdminTagsInput();
    document.getElementById("formBestReview").value = p.best_review || "";
    document.getElementById("formWorstReview").value = p.worst_review || "";
    
    const imgEl = document.getElementById("formImageUrl");
    if (imgEl) {
      imgEl.value = p.image_url || "";
      updateImagePreview(p.image_url);
    }

    const chk = document.getElementById("formIsVerifiedReview");
    if (chk) chk.checked = true;

    alert(`✨ Đã tự động bóc tách thành công thông tin quán "${p.name}"! Bạn hãy kiểm tra lại và nhấn Lưu.`);
  } catch (err) {
    if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
      alert("❌ Không thể kết nối tới Backend! Vui lòng kiểm tra xem bạn đã chạy file MO_WEB_SGGO.bat chưa.");
    } else {
      alert("❌ Lỗi bóc tách: " + err.message);
    }
  } finally {
    btn.innerHTML = `<i class="fa-solid fa-bolt"></i> Tự Động Điền`;
    btn.disabled = false;
  }
}

function updateImagePreview(url) {
  const img = document.getElementById("formImagePreview");
  const noImg = document.getElementById("formImageNoPreview");
  if (img && noImg) {
    if (url && url.trim()) {
      img.src = url;
      img.classList.remove("hidden");
      noImg.classList.add("hidden");
      img.onerror = () => {
        img.classList.add("hidden");
        noImg.classList.remove("hidden");
      };
    } else {
      img.src = "";
      img.classList.add("hidden");
      noImg.classList.remove("hidden");
    }
  }
}

function openAddPlaceModal() {
  document.getElementById("placeFormTitle").innerText = "➕ Thêm Địa Điểm Mới Vào CSDL";
  document.getElementById("placeFormSubtitle").innerText = "Nhập dữ liệu địa điểm tại Sài Gòn vào CSDL SQLite";
  document.getElementById("btnSubmitPlaceForm").innerText = "➕ Lưu Địa Điểm Mới Vào SQLite";
  document.getElementById("gmapsExtractorBox").classList.remove("hidden");
  document.getElementById("gmapsExtractInput").value = "";
  document.getElementById("placeAdminForm").reset();
  document.getElementById("formPlaceId").value = "";
  document.getElementById("formName").value = "";
  document.getElementById("formCategory").value = "an_uong";
  document.getElementById("formDistrict").value = "TP.HCM";
  document.getElementById("formAddress").value = "";
  document.getElementById("formLat").value = "10.7550";
  document.getElementById("formLon").value = "106.6650";
  document.getElementById("formReviewsCount").value = "100";
  document.getElementById("formOpenTime").value = "08:00";
  document.getElementById("formCloseTime").value = "22:30";
  document.getElementById("formMinPrice").value = 30000;
  document.getElementById("formMaxPrice").value = 85000;
  document.getElementById("formRating").value = 4.5;
  document.getElementById("formPeakHours").value = "";
  ['di_1_minh', 'hen_ho', 'nhom_ban', 'gia_dinh'].forEach(t => {
    const c1 = document.getElementById(`chk_t1_${t}`);
    const c2 = document.getElementById(`chk_t2_${t}`);
    if (c1) c1.checked = false;
    if (c2) c2.checked = false;
  });
  // Mặc định quán mới: nhom_ban ở Tier 1
  const defT1 = document.getElementById("chk_t1_nhom_ban");
  if (defT1) defT1.checked = true;
  syncAdminTagsInput();
  document.getElementById("formBestReview").value = "";
  document.getElementById("formWorstReview").value = "";
  const chkRev = document.getElementById("formIsVerifiedReview");
  if (chkRev) chkRev.checked = true;
  const chkAdmin = document.getElementById("formIsAdminChoice");
  if (chkAdmin) chkAdmin.checked = false;
  const chkHidden = document.getElementById("formIsHidden");
  if (chkHidden) chkHidden.checked = false;
  document.getElementById("formImageUrl").value = "";
  updateImagePreview("");
  document.getElementById("modalPlaceForm").classList.remove("hidden");
}

async function openEditPlaceModalById(id) {
  let p = allPlacesCache.find(x => Number(x.id) === Number(id));
  if (!p) {
    try {
      const res = await fetch(`${API_BASE}/places/${id}`);
      if (res.ok) p = await res.json();
    } catch (e) {}
  }
  if (!p) {
    alert("Không tìm thấy thông tin địa điểm #" + id);
    return;
  }
  openEditPlaceModal(p);
}

function handleDeletePlaceById(id) {
  const p = allPlacesCache.find(x => Number(x.id) === Number(id));
  const name = p ? p.name : `#${id}`;
  handleDeletePlace(id, name);
}

function openEditPlaceModal(p) {
  document.getElementById("placeFormTitle").innerHTML = `<i class="fa-solid fa-pen-to-square text-blue-600 mr-1.5"></i> Chỉnh Sửa Quán #${p.id} — ${p.name}`;
  document.getElementById("placeFormSubtitle").innerText = "Đang chỉnh sửa dữ liệu quán đã có trong CSDL SQLite";
  document.getElementById("btnSubmitPlaceForm").innerText = `💾 Lưu Cập Nhật Cho Quán #${p.id}`;
  document.getElementById("gmapsExtractorBox").classList.add("hidden");
  document.getElementById("formPlaceId").value = p.id;
  document.getElementById("formName").value = p.name || "";
  document.getElementById("formCategory").value = p.category || "an_uong";
  document.getElementById("formDistrict").value = p.district || "TP.HCM";
  document.getElementById("formAddress").value = p.address || "";
  document.getElementById("formLat").value = (p.lat !== undefined && p.lat !== null) ? p.lat : 10.7550;
  document.getElementById("formLon").value = (p.lon !== undefined && p.lon !== null) ? p.lon : 106.6650;
  document.getElementById("formReviewsCount").value = p.reviews_count || 100;
  document.getElementById("formOpenTime").value = p.open_time || "08:00";
  document.getElementById("formCloseTime").value = p.close_time || "22:00";
  document.getElementById("formMinPrice").value = p.min_price || 0;
  document.getElementById("formMaxPrice").value = p.max_price || 0;
  document.getElementById("formRating").value = p.rating || 4.5;
  document.getElementById("formPeakHours").value = p.peak_hours || "";
  const pDispEl = document.getElementById("formPriceDisplay");
  if (pDispEl) pDispEl.value = p.price_display || "";
  document.getElementById("formTags").value = p.tags || "nhom_ban";
  document.getElementById("formBestReview").value = p.best_review || "";
  document.getElementById("formWorstReview").value = p.worst_review || "";
  const chkRev = document.getElementById("formIsVerifiedReview");
  if (chkRev) chkRev.checked = (p.is_verified_review === 1);
  const chkAdmin = document.getElementById("formIsAdminChoice");
  if (chkAdmin) chkAdmin.checked = (p.is_admin_choice === 1);
  const chkHidden = document.getElementById("formIsHidden");
  if (chkHidden) chkHidden.checked = (p.is_hidden === 1);
  document.getElementById("formImageUrl").value = p.image_url || "";
  updateImagePreview(p.image_url || "");
  document.getElementById("modalPlaceForm").classList.remove("hidden");
}

function closePlaceFormModal() {
  document.getElementById("modalPlaceForm").classList.add("hidden");
}

async function handleSavePlace(e) {
  e.preventDefault();
  syncAdminTagsInput();
  const placeId = document.getElementById("formPlaceId").value;
  const isEdit = placeId !== "";
  const chkRev = document.getElementById("formIsVerifiedReview");
  const isRealReview = chkRev ? (chkRev.checked ? 1 : 0) : 1;
  const chkAdmin = document.getElementById("formIsAdminChoice");
  const isAdminChoice = chkAdmin ? (chkAdmin.checked ? 1 : 0) : 0;
  const chkHidden = document.getElementById("formIsHidden");
  const isHidden = chkHidden ? (chkHidden.checked ? 1 : 0) : 0;

  const rawImg = document.getElementById("formImageUrl").value.trim();
  const payload = {
    name: document.getElementById("formName").value.trim(),
    category: document.getElementById("formCategory").value,
    address: document.getElementById("formAddress").value.trim(),
    district: document.getElementById("formDistrict").value.trim() || "TP.HCM",
    lat: parseFloat(document.getElementById("formLat")?.value || 10.7550),
    lon: parseFloat(document.getElementById("formLon")?.value || 106.6650),
    reviews_count: parseInt(document.getElementById("formReviewsCount")?.value || 100),
    open_time: document.getElementById("formOpenTime").value.trim(),
    close_time: document.getElementById("formCloseTime").value.trim(),
    min_price: parseInt(document.getElementById("formMinPrice").value) || 0,
    max_price: parseInt(document.getElementById("formMaxPrice").value) || 0,
    rating: parseFloat(document.getElementById("formRating").value) || 4.5,
    peak_hours: document.getElementById("formPeakHours").value.trim(),
    tags: document.getElementById("formTags").value.trim(),
    price_display: document.getElementById("formPriceDisplay")?.value.trim() || null,
    best_review: document.getElementById("formBestReview").value.trim(),
    worst_review: document.getElementById("formWorstReview").value.trim(),
    image_url: rawImg ? rawImg : null,
    is_verified: 1,
    is_verified_review: isRealReview,
    is_admin_choice: isAdminChoice,
    is_hidden: isHidden
  };

  const url = isEdit ? `${API_BASE}/admin/places/${placeId}` : `${API_BASE}/admin/places`;
  const method = isEdit ? "PUT" : "POST";

  try {
    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Không thể lưu dữ liệu.");
    }

    alert(isEdit 
      ? `✅ Đã cập nhật thành công quán "${payload.name}" (#${placeId}) vào CSDL SQLite!` 
      : `✅ Đã thêm địa điểm mới "${payload.name}" vào CSDL SQLite!`
    );
    closePlaceFormModal();
    await preloadPlaces();
    const viewAdmin = document.getElementById("viewAdmin");
    if (viewAdmin && !viewAdmin.classList.contains("hidden")) {
      loadAdminDashboard();
    }
    const viewAll = document.getElementById("viewAll");
    if (viewAll && !viewAll.classList.contains("hidden")) {
      renderAllPlaces(allPlacesCache);
    }
  } catch (err) {
    alert("❌ Lỗi: " + err.message);
  }
}

async function handleDeletePlace(placeId, name) {
  if (!confirm(`Bạn có chắc chắn muốn xóa địa điểm "${name}" khỏi CSDL SQLite không?`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/admin/places/${placeId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Không thể xóa địa điểm.");
    alert("✅ Đã xóa địa điểm thành công!");
    preloadPlaces();
    loadAdminDashboard();
  } catch (err) {
    alert("❌ Lỗi: " + err.message);
  }
}

// ==============================================================================
// 7. TẢI VÀ NHẬP CSV (IMPORT / EXPORT)
// ==============================================================================

let fileToUploadBase64 = "";
let uploadedFileName = "";

function downloadCSVTemplate() {
  window.location.href = `${API_BASE}/admin/sample-csv`;
}

function downloadExcelTemplate() {
  window.location.href = `${API_BASE}/admin/sample-excel`;
}

function openImportModal() {
  csvToUploadText = "";
  fileToUploadBase64 = "";
  uploadedFileName = "";
  const inp = document.getElementById("csvFileInput");
  if (inp) inp.value = "";
  document.getElementById("csvFileName").innerText = "Hỗ trợ định dạng .csv, .xlsx, .xls";
  document.getElementById("btnUploadCSV").disabled = true;
  const reportBox = document.getElementById("csvValidationReport");
  if (reportBox) reportBox.classList.add("hidden");
  document.getElementById("modalImportCSV").classList.remove("hidden");
}

function closeImportModal() {
  document.getElementById("modalImportCSV").classList.add("hidden");
}

function handleCSVFileSelected(e) {
  const file = e.target.files[0];
  if (!file) return;

  uploadedFileName = file.name;
  document.getElementById("csvFileName").innerText = `Đã chọn: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  const isExcel = file.name.toLowerCase().endsWith(".xlsx") || file.name.toLowerCase().endsWith(".xls");
  const reader = new FileReader();

  if (isExcel) {
    reader.onload = function(evt) {
      fileToUploadBase64 = evt.target.result; // Data URL containing base64
      csvToUploadText = "";
      document.getElementById("btnUploadCSV").disabled = false;
    };
    reader.readAsDataURL(file);
  } else {
    reader.onload = function(evt) {
      csvToUploadText = evt.target.result;
      fileToUploadBase64 = "";
      document.getElementById("btnUploadCSV").disabled = false;
    };
    reader.readAsText(file, "UTF-8");
  }
}

async function submitCSVImport() {
  if (!csvToUploadText && !fileToUploadBase64) return;
  const btn = document.getElementById("btnUploadCSV");
  const reportBox = document.getElementById("csvValidationReport");
  const errorListEl = document.getElementById("csvErrorList");
  const titleEl = document.getElementById("csvValidationTitle");

  btn.innerText = "Đang kiểm tra & nạp CSDL...";
  btn.disabled = true;

  try {
    const payload = {
      filename: uploadedFileName || "places_import.csv"
    };
    if (fileToUploadBase64) {
      payload.file_base64 = fileToUploadBase64;
    } else {
      payload.csv_content = csvToUploadText;
    }

    const res = await fetch(`${API_BASE}/admin/import-csv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.error_count > 0) {
      if (reportBox) reportBox.classList.remove("hidden");
      if (titleEl) titleEl.innerText = `Đã nạp ${data.imported_count}/${data.total_rows} dòng. Phát hiện ${data.error_count} dòng lỗi:`;
      if (errorListEl) {
        errorListEl.innerHTML = "";
        data.errors.forEach(err => {
          errorListEl.innerHTML += `<li><strong>Dòng ${err.row}</strong> (Cột <code class="font-bold text-rose-700 bg-rose-100 px-1 py-0.5 rounded">${err.field}</code>): ${err.reason}</li>`;
        });
      }
      if (data.imported_count > 0) {
        preloadPlaces();
        loadAdminDashboard();
      }
    } else {
      if (reportBox) reportBox.classList.add("hidden");
      alert(`🎉 Toàn bộ ${data.imported_count} địa điểm hợp lệ và đã nạp thành công vào CSDL SQLite!`);
      closeImportModal();
      preloadPlaces();
      loadAdminDashboard();
    }
  } catch (e) {
    alert("❌ Lỗi khi nạp file CSV: " + (e.message || "Không thể kết nối máy chủ."));
  } finally {
    btn.innerText = "Tiến Hành Nạp Dữ Liệu";
    btn.disabled = false;
  }
}

// ==============================================================================
// 8. XEM CHI TIẾT ĐỊA ĐIỂM CHUẨN GOOGLE MAPS (ẢNH, THÔNG TIN, COMMENT, BẢN ĐỒ)
// ==============================================================================

let currentDetailPlace = null;

function openPlaceDetailById(id) {
  let p = allPlacesCache.find(x => Number(x.id) === Number(id));
  if (!p) return;

  currentDetailPlace = p;

  // 1. Phân loại & Huy hiệu Admin Pick
  const isEat = p.category === "an_uong";
  const catLabel = document.getElementById("detailCategoryLabel");
  if (catLabel) catLabel.innerText = isEat ? "Ẩm thực Sài Gòn" : "Vui chơi & Di tích";

  const adminBadge = document.getElementById("detailAdminChoiceBadge");
  if (adminBadge) {
    if (p.is_admin_choice === 1) {
      adminBadge.classList.remove("hidden");
      adminBadge.classList.add("inline-flex");
    } else {
      adminBadge.classList.add("hidden");
      adminBadge.classList.remove("inline-flex");
    }
  }

  // 2. Banner Ảnh thực tế / Placeholder chuẩn
  const imgWrapper = document.getElementById("detailImageWrapper");
  if (imgWrapper) {
    if (p.image_url && p.image_url.trim()) {
      imgWrapper.innerHTML = `
        <img src="${p.image_url}" alt="${p.name}" class="w-full h-full object-cover" onerror="this.parentElement.innerHTML='<div class=\\'w-full h-full flex flex-col items-center justify-center bg-slate-100 text-slate-400 font-bold text-xs gap-1.5\\'><i class=\\'fa-solid fa-camera text-2xl text-slate-300\\'></i> Chưa có ảnh thực tế</div>'" />
        <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none"></div>
        <div class="absolute bottom-3 left-4 right-4 flex justify-between items-center text-white text-xs font-bold drop-shadow">
          <span>#${p.id} • ${p.district || 'TP.HCM'}</span>
          <span class="bg-black/40 backdrop-blur-sm px-2 py-0.5 rounded-md text-[10px]"><i class="fa-solid fa-camera mr-1"></i> Ảnh thực tế</span>
        </div>
      `;
    } else {
      imgWrapper.innerHTML = `
        <div class="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-slate-100 via-slate-50 to-orange-50/40 text-slate-400 font-bold text-xs gap-1.5 p-4 text-center">
          <div class="w-12 h-12 rounded-2xl bg-white shadow-xs border border-slate-200 flex items-center justify-center text-slate-300 text-xl">
            <i class="fa-solid fa-camera"></i>
          </div>
          <span class="text-slate-600 font-extrabold text-sm">Chưa có ảnh thực tế</span>
          <span class="text-[11px] text-slate-400 font-normal">SGGo cam kết chỉ hiển thị ảnh thật, không dùng ảnh mạng giả lập</span>
        </div>
      `;
    }
  }

  // 3. Tên, Số sao & Mức giá
  const titleEl = document.getElementById("detailTitle");
  if (titleEl) titleEl.innerText = p.name;

  const ratingBadge = document.getElementById("detailRatingBadge");
  if (ratingBadge) ratingBadge.innerText = `⭐ ${p.rating}`;

  // Đổ bóng sao vàng
  const starContainer = document.getElementById("detailStarIcons");
  if (starContainer) {
    const fullStars = Math.floor(p.rating);
    const halfStar = (p.rating % 1) >= 0.3;
    let starsHtml = "";
    for (let i = 0; i < fullStars; i++) starsHtml += `<i class="fa-solid fa-star"></i>`;
    if (halfStar) starsHtml += `<i class="fa-solid fa-star-half-stroke"></i>`;
    const emptyStars = 5 - Math.ceil(p.rating);
    for (let i = 0; i < emptyStars; i++) starsHtml += `<i class="fa-regular fa-star text-slate-300"></i>`;
    starContainer.innerHTML = starsHtml;
  }

  const reviewsCountEl = document.getElementById("detailReviewsCount");
  if (reviewsCountEl) reviewsCountEl.innerText = `${p.reviews_count || 100} đánh giá Google`;

  const priceRangeEl = document.getElementById("detailPriceRange");
  if (priceRangeEl) {
    priceRangeEl.innerText = p.price_display
      ? p.price_display
      : ((p.min_price === 0 && p.max_price === 0)
        ? "Miễn phí vé vào cổng"
        : `${p.min_price ? p.min_price.toLocaleString() + 'đ' : ''} - ${p.max_price ? p.max_price.toLocaleString() + 'đ' : ''}`);
  }

  // 4. Link Google Maps
  const queryEnc = encodeURIComponent(`${p.name} ${p.address}`);
  const gmapsRouteUrl = `https://www.google.com/maps/search/?api=1&query=${queryEnc}`;

  const realPageBtn = document.getElementById("detailGmapsRealPageBtn");
  if (realPageBtn) realPageBtn.href = gmapsRouteUrl;

  const routeBtn = document.getElementById("detailGmapsRouteBtn");
  if (routeBtn) routeBtn.href = gmapsRouteUrl;

  const extMapLink = document.getElementById("detailExternalMapLink");
  if (extMapLink) extMapLink.href = gmapsRouteUrl;

  // 5. Địa chỉ cụ thể
  const addrEl = document.getElementById("detailAddress");
  if (addrEl) addrEl.innerText = p.address;

  // 6. Trạng thái hoạt động
  const isOpen = isPlaceCurrentlyOpen(p.open_time, p.close_time);
  const statusBadge = document.getElementById("detailStatusBadge");
  if (statusBadge) {
    statusBadge.className = isOpen
      ? "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800"
      : "px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800";
    statusBadge.innerText = isOpen ? "🟢 Đang mở cửa" : "🔴 Đã đóng cửa";
  }

  const openHoursEl = document.getElementById("detailOpenHours");
  if (openHoursEl) openHoursEl.innerText = p.hours_display || `${p.open_time} - ${p.close_time}`;

  // 7. Giờ cao điểm
  const peakHoursEl = document.getElementById("detailPeakHours");
  if (peakHoursEl) {
    const rawPeak = (p.peak_hours && p.peak_hours !== 'Chưa rõ') ? p.peak_hours : '';
    const cleanPeak = rawPeak.replace(/\s*\([^\)]*đông[^\)]*\)/gi, '').trim();
    peakHoursEl.innerText = cleanPeak || "Chưa rõ (quán chưa cập nhật)";
  }

  // 8. Bối cảnh tags (Xếp trên/dưới tự nhiên, KHÔNG ghi chữ Tier 1/2, KHÔNG làm nổi bật lệch màu)
  const tagsContainer = document.getElementById("detailTagsList");
  if (tagsContainer) {
    tagsContainer.innerHTML = "";
    const tagMap = {
      di_1_minh: "🎧 Đi 1 mình",
      hen_ho: "💑 Hẹn hò cặp đôi",
      nhom_ban: "🎉 Nhóm bạn",
      gia_dinh: "👨‍👩‍👧‍👦 Gia đình"
    };
    const { tier1, tier2 } = parsePlaceTiers(p.tags || "");

    let html = `<div class="w-full space-y-1.5 mt-1">`;
    if (tier1.length > 0) {
      html += `
        <div class="flex items-center gap-1.5 flex-wrap">
          ${tier1.map(t => `<span class="px-2.5 py-1 bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold">${tagMap[t] || t}</span>`).join("")}
        </div>
      `;
    }
    if (tier2.length > 0) {
      html += `
        <div class="flex items-center gap-1.5 flex-wrap">
          ${tier2.map(t => `<span class="px-2.5 py-1 bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold">${tagMap[t] || t}</span>`).join("")}
        </div>
      `;
    }
    html += `</div>`;
    tagsContainer.innerHTML = html;
  }

  // 9. Bình luận khen & lưu ý thực tế
  const bestRev = document.getElementById("detailBestReview");
  if (bestRev) {
    if (p.best_review && p.best_review.trim()) {
      bestRev.innerText = p.best_review;
    } else {
      bestRev.innerHTML = `<span class="text-slate-400 font-normal italic">Chưa có đánh giá 5 sao nào được ghi nhận trên Google Maps.</span>`;
    }
  }

  const worstRev = document.getElementById("detailWorstReview");
  if (worstRev) {
    if (p.worst_review && p.worst_review.trim()) {
      worstRev.innerText = p.worst_review;
    } else {
      worstRev.innerHTML = `<span class="text-slate-400 font-normal italic">Chưa có phản ánh hoặc góp ý tiêu cực nào trên Google Maps.</span>`;
    }
  }

  // 10. Bản đồ tương tác Leaflet (Không bị Google Maps chặn)
  const drawerMapContainer = document.getElementById("drawerLeafletMap");
  if (drawerMapContainer && typeof L !== "undefined") {
    const lat = p.lat || 10.755;
    const lon = p.lon || 106.665;
    if (!drawerMap) {
      drawerMap = L.map("drawerLeafletMap", {
        zoomControl: true,
        scrollWheelZoom: false
      }).setView([lat, lon], 16);

      initLeafletTileLayers(drawerMap);

      const pinIcon = L.divIcon({
        className: "custom-leaflet-marker",
        html: `<div style="background-color: #E11D48; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 2.5px solid white;"><i class="fa-solid fa-location-dot"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
      });

      drawerMarker = L.marker([lat, lon], { icon: pinIcon }).addTo(drawerMap);
      drawerMarker.bindPopup(`<strong>${p.name}</strong><br><span style="font-size:11px;">${p.address}</span>`);
    } else {
      drawerMap.setView([lat, lon], 16);
      if (drawerMarker) {
        drawerMarker.setLatLng([lat, lon]);
        drawerMarker.bindPopup(`<strong>${p.name}</strong><br><span style="font-size:11px;">${p.address}</span>`);
      }
    }
    setTimeout(() => {
      if (drawerMap) drawerMap.invalidateSize();
    }, 350);
  }

  // 11. Nút sửa dành cho Admin
  const footerAdminBtn = document.getElementById("detailFooterAdminEditBtn");
  if (footerAdminBtn) {
    if (currentUser && currentUser.role === "admin") {
      footerAdminBtn.innerHTML = `
        <button onclick="closePlaceDetail(); openEditPlaceModalById(${p.id});" class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-xs cursor-pointer">
          <i class="fa-solid fa-pen-to-square"></i> <span>Sửa quán này</span>
        </button>
      `;
    } else {
      footerAdminBtn.innerHTML = ``;
    }
  }

  // Mở ngăn kéo
  const backdrop = document.getElementById("placeDetailBackdrop");
  const drawer = document.getElementById("placeDetailDrawer");
  if (backdrop) backdrop.classList.remove("hidden");
  if (drawer) drawer.classList.remove("translate-x-full");
}

function closePlaceDetail() {
  const backdrop = document.getElementById("placeDetailBackdrop");
  const drawer = document.getElementById("placeDetailDrawer");

  if (drawer) drawer.classList.add("translate-x-full");
  if (backdrop) backdrop.classList.add("hidden");
  currentDetailPlace = null;
}

function copyDetailAddress() {
  if (!currentDetailPlace) return;
  const text = `${currentDetailPlace.name}, ${currentDetailPlace.address}`;
  navigator.clipboard.writeText(text).then(() => {
    alert(`📋 Đã sao chép địa chỉ:\n"${text}"\nBạn có thể dán vào Grab, Be hoặc ứng dụng bản đồ!`);
  }).catch(() => {
    prompt("Sao chép địa chỉ:", text);
  });
}



// Giữ lại alias để tương thích các link cũ
function openSideMapById(id) {
  openPlaceDetailById(id);
}

function closeSideMap() {
  closePlaceDetail();
}

function copySideMapAddress() {
  copyDetailAddress();
}

// ==========================================
// QUẢN LÝ TAG & BỘ LỌC (G6-FR08 & Section 5 ERD)
// ==========================================
async function loadAdminTags() {
  const tbody = document.getElementById("adminTagsTable");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Đang tải danh mục tag...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/admin/tags`);
    const data = await res.json();
    const tags = data.tags || [];
    const countBadge = document.getElementById("adminTagCountBadge");
    if (countBadge) countBadge.innerText = tags.length;
    renderAdminTagsTable(tags);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-rose-500 font-semibold">❌ Lỗi tải tags: ${err.message}</td></tr>`;
  }
}

function renderAdminTagsTable(tags) {
  const tbody = document.getElementById("adminTagsTable");
  if (!tbody) return;
  if (!tags || tags.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400 font-medium">Chưa có tag nào trong hệ thống.</td></tr>`;
    return;
  }

  tbody.innerHTML = tags.map(t => {
    const isActive = (t.is_active === 1);
    const tierBadge = t.tier_type === 'companion' 
      ? `<span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-rose-50 text-[#E11D48] border border-rose-200">Bạn đồng hành (Tier 1/2)</span>`
      : `<span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-blue-50 text-blue-700 border border-blue-200">Tiện ích / Không gian</span>`;

    return `
      <tr class="hover:bg-slate-50/80 transition">
        <td class="p-3.5 font-bold text-slate-400">#${t.id}</td>
        <td class="p-3.5 font-mono font-bold text-slate-800 text-xs">${t.tag_key}</td>
        <td class="p-3.5 font-bold text-slate-900">${t.name}</td>
        <td class="p-3.5">${tierBadge}</td>
        <td class="p-3.5">
          <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
            <i class="fa-solid fa-store text-[9px] text-[#E11D48]"></i> ${t.place_count || 0} quán
          </span>
        </td>
        <td class="p-3.5">
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${isActive ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-500 border border-slate-200'}">
            <span class="w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-500' : 'bg-slate-400'}"></span>
            ${isActive ? 'Đang kích hoạt' : 'Đã ẩn'}
          </span>
        </td>
        <td class="p-3.5 text-center bg-slate-50/50 border-l border-slate-200">
          <div class="inline-flex items-center gap-1.5">
            <button onclick="handleToggleTag(${t.id}, ${isActive ? 0 : 1})" title="${isActive ? 'Tắt tag' : 'Bật tag'}" class="px-2.5 py-1 rounded-lg text-[11px] font-bold ${isActive ? 'bg-amber-100 hover:bg-amber-200 text-amber-900' : 'bg-emerald-100 hover:bg-emerald-200 text-emerald-900'} transition cursor-pointer">
              ${isActive ? 'Tắt' : 'Bật'}
            </button>
            <button onclick="handleDeleteTag(${t.id}, '${t.name}')" title="Xóa tag" class="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition cursor-pointer">
              <i class="fa-regular fa-trash-can text-xs"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function openAddTagModal() {
  const m = document.getElementById("modalAddTag");
  if (m) m.classList.remove("hidden");
}

function closeAddTagModal() {
  const m = document.getElementById("modalAddTag");
  if (m) m.classList.add("hidden");
}

async function handleSaveTag(e) {
  e.preventDefault();
  const tagKey = document.getElementById("newTagKey")?.value.trim();
  const tagName = document.getElementById("newTagName")?.value.trim();
  const tierType = document.getElementById("newTagTierType")?.value || "companion";

  if (!tagKey || !tagName) {
    alert("Vui lòng điền đầy đủ mã tag và tên hiển thị!");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/admin/tags`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tag_key: tagKey, name: tagName, tier_type: tierType })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Không thể thêm tag");

    alert("✅ Đã thêm tag mới thành công!");
    closeAddTagModal();
    document.getElementById("newTagKey").value = "";
    document.getElementById("newTagName").value = "";
    loadAdminTags();
  } catch (err) {
    alert("❌ Lỗi: " + err.message);
  }
}

async function handleToggleTag(tagId, targetActive) {
  try {
    const res = await fetch(`${API_BASE}/admin/tags/${tagId}/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: targetActive })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Không thể đổi trạng thái tag");
    loadAdminTags();
  } catch (err) {
    alert("❌ Lỗi: " + err.message);
  }
}

async function handleDeleteTag(tagId, tagName) {
  if (!confirm(`Bạn có chắc chắn muốn xóa tag "${tagName}"?`)) return;
  try {
    const res = await fetch(`${API_BASE}/admin/tags/${tagId}`, {
      method: "DELETE"
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Không thể xóa tag");
    loadAdminTags();
  } catch (err) {
    alert("❌ Lỗi: " + err.message);
  }
}
