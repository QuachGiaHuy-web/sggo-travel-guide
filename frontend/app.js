// SGGo! Frontend Application Core
const API_BASE = "http://localhost:8000";

let map = null;
let currentPlaces = [];
let placeMarkers = [];

function initMap() {
  map = L.map('map').setView([10.7550, 106.6650], 15);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(map);
}

document.addEventListener('DOMContentLoaded', () => {
  initMap();
});

async function loadPlaces() {
  try {
    const res = await fetch(`${API_BASE}/api/places`);
    const data = await res.json();
    currentPlaces = data.places || [];
    renderPlacesCards(currentPlaces);
  } catch (err) {
    console.error("Lỗi khi tải danh sách địa điểm:", err);
  }
}

function renderPlacesCards(places) {
  const container = document.getElementById('placesContainer');
  if (!container) return;
  
  if (places.length === 0) {
    container.innerHTML = `<div class="empty-state">Không có địa điểm phù hợp</div>`;
    return;
  }

  container.innerHTML = places.map(p => `
    <div class="place-card" data-id="${p.id}">
      <div class="place-card-img" style="background-image: url('${p.image_url || 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500'}')">
        <span class="category-tag ${p.category === 'an_uong' ? 'tag-food' : 'tag-heritage'}">
          ${p.category === 'an_uong' ? 'Ẩm Thực' : 'Di Sản'}
        </span>
      </div>
      <div class="place-card-body">
        <h3 class="place-name">${p.name}</h3>
        <p class="place-address">${p.address}</p>
        <div class="place-meta">
          <span class="rating">⭐ ${p.rating.toFixed(1)}</span>
          <span class="price">${p.min_price > 0 ? (p.min_price/1000) + 'k - ' + (p.max_price/1000) + 'k' : 'Miễn phí'}</span>
        </div>
      </div>
    </div>
  `).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  loadPlaces();
});

function createMarkerIcon(category) {
  const isFood = category === 'an_uong';
  const color = isFood ? '#FF5733' : '#0284C7';
  const iconSymbol = isFood ? '🍜' : '🏛️';

  return L.divIcon({
    className: 'custom-map-pin',
    html: `<div class="pin-inner" style="background-color: ${color};">
             <span class="pin-symbol">${iconSymbol}</span>
           </div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 36],
    popupAnchor: [0, -32]
  });
}

function renderMapMarkers(places) {
  // Xóa marker cũ
  placeMarkers.forEach(m => map.removeLayer(m));
  placeMarkers = [];

  places.forEach(p => {
    if (!p.lat || !p.lon) return;
    const icon = createMarkerIcon(p.category);
    const marker = L.marker([p.lat, p.lon], { icon: icon }).addTo(map);
    marker.placeData = p;
    placeMarkers.push(marker);
  });
}

function bindMarkerPopups() {
  placeMarkers.forEach(marker => {
    const p = marker.placeData;
    const popupContent = `
      <div class="map-popup-card">
        <h4>${p.name}</h4>
        <p class="popup-addr">${p.address}</p>
        <div class="popup-meta">
          <span>⭐ ${p.rating.toFixed(1)}</span>
          <span>🕒 ${p.open_time} - ${p.close_time}</span>
        </div>
      </div>
    `;
    marker.bindPopup(popupContent);
  });
}

function openPlaceModal(placeId) {
  const p = currentPlaces.find(x => x.id === parseInt(placeId));
  if (!p) return;

  document.getElementById('modalName').textContent = p.name;
  document.getElementById('modalAddress').textContent = p.address;
  document.getElementById('modalHours').textContent = `${p.open_time} - ${p.close_time}`;
  document.getElementById('modalPrice').textContent = p.min_price > 0 ? `${(p.min_price/1000)}k - ${(p.max_price/1000)}k VNĐ` : 'Miễn phí vé vào';
  document.getElementById('modalRating').textContent = `⭐ ${p.rating.toFixed(1)} (${p.reviews_count} đánh giá)`;

  const cover = document.getElementById('modalCover');
  cover.style.backgroundImage = `url('${p.image_url || 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500'}')`;

  document.getElementById('placeDetailModal').style.display = 'flex';
}

function closePlaceModal() {
  document.getElementById('placeDetailModal').style.display = 'none';
}

// Keyboard & Backdrop dismissal for modal
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closePlaceModal();
  }
});

document.addEventListener('click', (e) => {
  const modal = document.getElementById('placeDetailModal');
  if (e.target === modal) {
    closePlaceModal();
  }
});

function filterByCategory(category) {
  let filtered = currentPlaces;
  if (category && category !== 'all') {
    filtered = currentPlaces.filter(p => p.category === category);
  }
  renderPlacesCards(filtered);
  renderMapMarkers(filtered);
  bindMarkerPopups();
}

function debounce(func, delay = 250) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, args), delay);
  };
}

function removeVietnameseTones(str) {
  str = str.replace(/à|á|ạ|ả|ã|â|ầ|ấ|ậ|ẩ|ẫ|ă|ằ|ắ|ặ|ẳ|ẵ/g, "a");
  str = str.replace(/è|é|ẹ|ẻ|ẽ|ê|ề|ế|ệ|ể|ễ/g, "e");
  str = str.replace(/ì|í|ị|ỉ|ĩ/g, "i");
  str = str.replace(/ò|ó|ọ|ỏ|õ|ô|ồ|ố|ộ|ổ|ỗ|ơ|ờ|ớ|ợ|ở|ỡ/g, "o");
  str = str.replace(/ù|ú|ụ|ủ|ũ|ư|ừ|ứ|ự|ử|ữ/g, "u");
  str = str.replace(/ỳ|ý|ỵ|ỷ|ỹ/g, "y");
  str = str.replace(/đ/g, "d");
  str = str.replace(/À|Á|Ạ|Ả|Ã|Â|Ầ|Ấ|Ậ|Ẩ|Ẫ|Ă|Ằ|Ắ|Ặ|Ẳ|Ẵ/g, "A");
  str = str.replace(/È|É|Ẹ|Ẻ|Ẽ|Ê|Ề|Ế|Ệ|Ể|Ễ/g, "E");
  str = str.replace(/Ì|Í|Ị|Ỉ|Ĩ/g, "I");
  str = str.replace(/Ò|Ó|Ọ|Ỏ|Õ|Ô|Ồ|Ố|Ộ|Ổ|Ỗ|Ơ|Ờ|Ớ|Ợ|Ở|Ỡ/g, "O");
  str = str.replace(/Ù|Ú|Ụ|Ủ|Ũ|Ư|Ừ|Ứ|Ự|Ử|Ữ/g, "U");
  str = str.replace(/Ỳ|Ý|Ỵ|Ỷ|Ỹ/g, "Y");
  str = str.replace(/Đ/g, "D");
  return str.toLowerCase().trim();
}

function handleSearch(query) {
  const normQuery = removeVietnameseTones(query);
  const matched = currentPlaces.filter(p => {
    const normName = removeVietnameseTones(p.name);
    const normAddr = removeVietnameseTones(p.address);
    return normName.includes(normQuery) || normAddr.includes(normQuery);
  });
  renderPlacesCards(matched);
  renderMapMarkers(matched);
  bindMarkerPopups();
}

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', debounce((e) => {
      const q = e.target.value.trim();
      if (!q) {
        renderPlacesCards(currentPlaces);
        renderMapMarkers(currentPlaces);
        bindMarkerPopups();
      } else {
        handleSearch(q);
      }
    }, 200));
  }
});

let userLocation = null;
let userMarker = null;

function locateUser() {
  if (!navigator.geolocation) {
    alert("Trình duyệt của bạn không hỗ trợ định vị GPS.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      userLocation = {
        lat: pos.coords.latitude,
        lon: pos.coords.longitude
      };
      renderUserLocationPin(userLocation);
      map.setView([userLocation.lat, userLocation.lon], 16);
    },
    (err) => {
      console.warn("Không thể lấy vị trí GPS:", err.message);
      // Fallback mặc định: Chợ An Đông, Quận 5
      userLocation = { lat: 10.7550, lon: 106.6690 };
      renderUserLocationPin(userLocation);
    }
  );
}

function renderUserLocationPin(loc) {
  if (userMarker) {
    map.removeLayer(userMarker);
  }
  const userIcon = L.divIcon({
    className: 'user-gps-pin',
    html: `<div class="user-gps-pulse"></div><div class="user-gps-core"></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });
  userMarker = L.marker([loc.lat, loc.lon], { icon: userIcon }).addTo(map);
  userMarker.bindPopup("<b>Vị trí của bạn</b><br>Điểm xuất phát chuyến đi").openPopup();
}

function setCustomStartingPoint(lat, lon, label = "Điểm hẹn đã chọn") {
  userLocation = { lat: parseFloat(lat), lon: parseFloat(lon) };
  renderUserLocationPin(userLocation);
  map.setView([userLocation.lat, userLocation.lon], 16);
}

function calculateDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371.0;
  const toRad = deg => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 10) / 10; // làm tròn 1 chữ số thập phân
}

function updateDistancesOnCards() {
  if (!userLocation) return;
  currentPlaces.forEach(p => {
    p.dist_km = calculateDistanceKm(userLocation.lat, userLocation.lon, p.lat, p.lon);
  });
  renderPlacesCards(currentPlaces);
}

function sortPlaces(criteria) {
  if (criteria === 'nearest' && userLocation) {
    currentPlaces.sort((a, b) => (a.dist_km || 999) - (b.dist_km || 999));
  } else if (criteria === 'rating') {
    currentPlaces.sort((a, b) => b.rating - a.rating);
  } else if (criteria === 'price_asc') {
    currentPlaces.sort((a, b) => a.min_price - b.min_price);
  }
  renderPlacesCards(currentPlaces);
}

let selectedItineraryPlaces = [];

function toggleItineraryPlace(placeId) {
  const p = currentPlaces.find(x => x.id === parseInt(placeId));
  if (!p) return;

  const idx = selectedItineraryPlaces.findIndex(x => x.id === p.id);
  if (idx > -1) {
    selectedItineraryPlaces.splice(idx, 1);
  } else {
    selectedItineraryPlaces.push(p);
  }
  updateItineraryDrawerUI();
}

function updateItineraryDrawerUI() {
  const countSpan = document.getElementById('itineraryCount');
  const stopsList = document.getElementById('itineraryStopsList');
  if (countSpan) countSpan.textContent = selectedItineraryPlaces.length;

  if (!stopsList) return;
  if (selectedItineraryPlaces.length === 0) {
    stopsList.innerHTML = `<p class="drawer-empty">Chưa có điểm nào trong lịch trình.</p>`;
    return;
  }

  stopsList.innerHTML = selectedItineraryPlaces.map((p, i) => `
    <div class="itinerary-stop-item">
      <span class="stop-num">${i + 1}</span>
      <div class="stop-info">
        <h4>${p.name}</h4>
        <p>${p.category === 'an_uong' ? '🍜 Ẩm thực' : '🏛️ Di sản'}</p>
      </div>
      <button class="btn-remove-stop" onclick="toggleItineraryPlace(${p.id})">&times;</button>
    </div>
  `).join('');
}

function clearItinerary() {
  selectedItineraryPlaces = [];
  updateItineraryDrawerUI();
  if (activeRoutePolyline) {
    map.removeLayer(activeRoutePolyline);
    activeRoutePolyline = null;
  }
}

async function optimizeTripRoute() {
  if (selectedItineraryPlaces.length === 0) {
    alert("Vui lòng chọn ít nhất 1 địa điểm để tối ưu!");
    return;
  }
  
  const startLat = userLocation ? userLocation.lat : 10.7550;
  const startLon = userLocation ? userLocation.lon : 106.6650;
  const placeIds = selectedItineraryPlaces.map(p => p.id);

  try {
    const res = await fetch(`${API_BASE}/api/route/optimize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start_lat: startLat,
        start_lon: startLon,
        place_ids: placeIds
      })
    });
    const data = await res.json();
    renderOptimizedPolyline(data.ordered_stops, { lat: startLat, lon: startLon });
  } catch (err) {
    console.error("Lỗi tối ưu lộ trình:", err);
  }
}

let activeRoutePolyline = null;

function renderOptimizedPolyline(stops, startCoord) {
  if (activeRoutePolyline) {
    map.removeLayer(activeRoutePolyline);
  }

  const latlngs = [[startCoord.lat, startCoord.lon]];
  stops.forEach(s => {
    latlngs.push([s.lat, s.lon]);
  });

  activeRoutePolyline = L.polyline(latlngs, {
    color: '#FF5733',
    weight: 5,
    opacity: 0.85,
    dashArray: '8, 8',
    lineCap: 'round'
  }).addTo(map);

  map.fitBounds(activeRoutePolyline.getBounds(), { padding: [50, 50] });
}

function computeTripDurations(totalKm) {
  // Đi bộ trung bình 4.5 km/h
  const walkMinutes = Math.round((totalKm / 4.5) * 60);
  // Xe máy nội thành 22 km/h
  const motoMinutes = Math.round((totalKm / 22) * 60);
  return { walkMinutes, motoMinutes };
}

function showAiLoadingState(isLoading) {
  let loader = document.getElementById('aiLoadingOverlay');
  if (isLoading) {
    if (!loader) {
      loader = document.createElement('div');
      loader.id = 'aiLoadingOverlay';
      loader.className = 'ai-loading-overlay';
      loader.innerHTML = `
        <div class="spinner"></div>
        <p class="loading-tip">Đang kết nối Gemini AI & phân tích bản đồ Chợ Lớn...</p>
      `;
      document.body.appendChild(loader);
    }
    loader.style.display = 'flex';
  } else if (loader) {
    loader.style.display = 'none';
  }
}

async function generateAiTrip() {
  const freeTime = document.getElementById('aiFreeTime')?.value || "14:00 - 18:30";
  const companion = document.getElementById('aiCompanion')?.value || "ban_be";
  closeAiModal();
  showAiLoadingState(true);

  try {
    const res = await fetch(`${API_BASE}/api/itinerary/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ free_time: freeTime, companion: companion, purpose: "ca_hai" })
    });
    const data = await res.json();
    showAiLoadingState(false);
    renderAiScheduleResult(data.itinerary);
  } catch (err) {
    showAiLoadingState(false);
    console.error("Lỗi sinh lịch trình AI:", err);
  }
}

function renderAiScheduleResult(itin) {
  alert(`✨ ${itin.trip_title}\n\n${itin.cultural_story}\n\nĐã gợi ý ${itin.schedule.length} trạm trải nghiệm!`);
}

function closeAiModal() {
  const m = document.getElementById('aiPlannerModal');
  if (m) m.style.display = 'none';
}
