// SGGo! Frontend Application Core
const API_BASE = "http://localhost:8000";

let map = null;
let currentPlaces = [];
let placeMarkers = [];

function initMap() {
  // Tọa độ trung tâm Quận 5 - Chợ Lớn
  map = L.map('map').setView([10.7550, 106.6650], 15);
}

document.addEventListener('DOMContentLoaded', () => {
  initMap();
});
