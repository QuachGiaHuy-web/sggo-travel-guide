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
