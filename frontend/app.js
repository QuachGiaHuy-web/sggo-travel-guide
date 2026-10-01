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
