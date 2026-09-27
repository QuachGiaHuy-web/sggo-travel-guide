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
